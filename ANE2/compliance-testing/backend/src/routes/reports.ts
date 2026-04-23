import { Router, Request, Response } from 'express';
import { query, getClient } from '../database/connection';
import axios from 'axios';

const router = Router();

// Health check para el router de reportes
router.get('/ping', (req: Request, res: Response) => {
  res.json({ status: 'ok', service: 'reports-router' });
});

// URL del microservicio Python
const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL || 'http://localhost:8000';

interface GeolocationResult {
  encontrado: boolean;
  resultado?: {
    central: {
      departamento: string;
      municipio: string;
      codigo_dane: string;
    };
    radio_km?: number;
    adyacentes?: Array<{
      departamento: string;
      municipio: string;
      codigo_dane: string;
    }>;
  };
}

/**
 * @swagger
 * /api/reports/compliance/{campaignId}:
 *   post:
 *     summary: Generar reporte de cumplimiento normativo
 *     description: Genera un reporte detallado de cumplimiento normativo para una campaña específica. El reporte incluye análisis de excursión de frecuencia (FM), análisis de profundidad de modulación (AM), verificación de límites normativos colombianos, geolocalización automática (departamento/municipio), y clasificación de cumplimiento por medición.
 *     tags: [Reports]
 *     parameters:
 *       - in: path
 *         name: campaignId
 *         required: true
 *         schema:
 *           type: integer
 *         description: ID de la campaña para generar el reporte
 *     responses:
 *       200:
 *         description: Reporte generado exitosamente
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/ComplianceReport'
 *       404:
 *         description: Campaña no encontrada o sin datos GPS
 *       500:
 *         description: Error generando el reporte
 */
router.post('/compliance/:campaignId', async (req: Request, res: Response) => {
  try {
    const campaignId = parseInt(req.params.campaignId);
    const forceRegenerate = req.query.force === 'true'; // Parámetro opcional para forzar regeneración
    
    // Obtener umbral del body o query params (default: 5)
    let requestedUmbral: number | null = null;
    if (req.body.umbral !== undefined) requestedUmbral = parseFloat(req.body.umbral);
    else if (req.query.umbral !== undefined) requestedUmbral = parseFloat(req.query.umbral as string);
    else if (req.body.umbral_db !== undefined) requestedUmbral = parseFloat(req.body.umbral_db);
    else if (req.query.umbral_db !== undefined) requestedUmbral = parseFloat(req.query.umbral_db as string);

    // Validar rango 0-10 si se proporciona
    if (requestedUmbral !== null) {
      if (isNaN(requestedUmbral) || requestedUmbral < 0) requestedUmbral = 0;
      // No limitamos estrictamente a 10 en backend, pero el frontend lo hará.
      // Python lo maneja como float positivo.
    }

    const UMBRAL_DB = requestedUmbral !== null ? requestedUmbral : 5;

    // 0. Verificar si ya existe un reporte cacheado
    // NOTA: El cache solo se usa para umbral=5 y sin especificar sensor (por compatibilidad con estructura actual de DB)
    const sensorMacQuery = req.query.sensor_mac as string;
    const useCache = !forceRegenerate && UMBRAL_DB === 5 && !sensorMacQuery;
    
    if (useCache) {
      const cachedReport = await query(`
        SELECT report_data, created_at, updated_at
        FROM compliance_reports_cache
        WHERE campaign_id = $1
      `, [campaignId]);

      if (cachedReport.rows.length > 0) {
        const cachedData = cachedReport.rows[0].report_data;
        // Verificar si el reporte cacheado tiene el mismo umbral
        // Si el reporte cacheado no tiene umbral guardado (versiones viejas), asumimos 5.
        const cachedUmbral = cachedData.umbral_db !== undefined ? cachedData.umbral_db : 5;
        
        // Si el umbral solicitado coincide con el cacheado, devolvemos cache
        // Usamos una pequeña tolerancia para floats
        if (Math.abs(cachedUmbral - UMBRAL_DB) < 0.01) {
          console.log(`✅ Returning cached report for campaign ${campaignId} (Umbral: ${cachedUmbral})`);
          return res.json({
            ...cachedData,
            cached: true,
            cache_created_at: cachedReport.rows[0].created_at,
            cache_updated_at: cachedReport.rows[0].updated_at
          });
        } else {
          console.log(`⚠️ Cached report has umbral ${cachedUmbral}, requested ${UMBRAL_DB}. Regenerating...`);
        }
      }
    } else {
      console.log(`🔄 Cache disabled for this request (umbral=${UMBRAL_DB}, sensor=${sensorMacQuery || 'auto'})`);
    }

    console.log(`🔄 Generating new report for campaign ${campaignId} with umbral ${UMBRAL_DB}dB...`);
    
    // 1. Obtener información de la campaña y validar sensor
    let campaignQuery = `
      SELECT c.*
      FROM campaigns c
      WHERE c.id = $1
    `;
    
    const campaignResult = await query(campaignQuery, [campaignId]);

    if (campaignResult.rows.length === 0) {
      return res.status(404).json({ error: 'Campaign not found' });
    }

    const campaign = campaignResult.rows[0];
    
    // Determinar qué sensor usar
    let sensorMac = sensorMacQuery;

    // Si no se especificó sensor, buscar uno asociado a la campaña (fallback)
    if (!sensorMac) {
      const sensorsResult = await query(`
        SELECT sensor_mac FROM campaign_sensors WHERE campaign_id = $1 LIMIT 1
      `, [campaignId]);
      
      if (sensorsResult.rows.length > 0) {
        sensorMac = sensorsResult.rows[0].sensor_mac;
      } else {
        return res.status(400).json({ error: 'Campaign has no sensors assigned' });
      }
    } else {
      // Validar que el sensor pertenezca a la campaña
      const validateSensor = await query(`
        SELECT 1 FROM campaign_sensors WHERE campaign_id = $1 AND sensor_mac = $2
      `, [campaignId, sensorMac]);
      
      if (validateSensor.rows.length === 0) {
        return res.status(400).json({ error: 'Sensor not assigned to this campaign' });
      }
    }

    // 2. Obtener la ubicación GPS
    let latitude: number | null = null;
    let longitude: number | null = null;

    // PRIORIDAD 1: GPS Manual configurado en la campaña
    if (campaign.config) {
      let configObj = campaign.config;
      if (typeof configObj === 'string') {
        try {
          configObj = JSON.parse(configObj);
        } catch (e) {
          console.error('Error parsing campaign config:', e);
        }
      }
      
      if (configObj.gps && (configObj.gps.lat !== undefined) && (configObj.gps.lng !== undefined)) {
        latitude = parseFloat(configObj.gps.lat);
        longitude = parseFloat(configObj.gps.lng);
        console.log(`📍 Using manual GPS from campaign config: ${latitude}, ${longitude}`);
      }
    }

    if (latitude === null || longitude === null) {
      // PRIORIDAD 2: Tabla sensors (ubicación fija)
      let gpsResult = await query(`
        SELECT lat, lng
        FROM sensors
        WHERE mac = $1 AND lat IS NOT NULL AND lng IS NOT NULL
        LIMIT 1
      `, [sensorMac]);

      // PRIORIDAD 3: Historial GPS (sensor_gps)
      if (gpsResult.rows.length === 0) {
        gpsResult = await query(`
          SELECT lat, lng
          FROM sensor_gps
          WHERE mac = $1
          ORDER BY created_at DESC
          LIMIT 1
        `, [sensorMac]);
      }

      if (gpsResult.rows.length > 0) {
        latitude = parseFloat(gpsResult.rows[0].lat);
        longitude = parseFloat(gpsResult.rows[0].lng);
      }
    }

    if (latitude === null || longitude === null) {
      return res.status(404).json({ error: 'No GPS data found for sensor (manual or automatic)' });
    }

    // 3. Consultar la API de geolocalización ANE
    let location: GeolocationResult;
    try {
      const geoResponse = await axios.post('http://172.23.80.220:4155/localizar', {
        lat: latitude,
        lon: longitude
      }, {
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        timeout: 10000
      });
      location = geoResponse.data;
    } catch (geoError) {
      console.error('Error calling geolocation API:', geoError);
      return res.status(503).json({ 
        error: 'Geolocation service unavailable',
        details: 'No se pudo conectar con el servicio de geolocalización ANE'
      });
    }

    if (!location.encontrado || !location.resultado || !location.resultado.central) {
      return res.status(404).json({ 
        error: 'Location not found',
        details: 'Las coordenadas no están dentro del territorio nacional'
      });
    }

    const { municipio, departamento, codigo_dane } = location.resultado.central;

    // Validar que tengamos el código DANE necesario para el análisis
    if (!codigo_dane) {
      console.warn('⚠️  No se obtuvo código DANE de la geolocalización');
      return res.status(400).json({ 
        error: 'DANE code not available',
        details: 'El código DANE es requerido para el análisis de cumplimiento. Verifica que el servicio de geolocalización esté funcionando correctamente.'
      });
    }

    // Recopilar DANE central y adyacentes
    const danesSet = new Set<string>();
    danesSet.add(String(codigo_dane).trim());

    if (location.resultado.adyacentes && Array.isArray(location.resultado.adyacentes)) {
      location.resultado.adyacentes.forEach(adj => {
        if (adj.codigo_dane) {
          danesSet.add(String(adj.codigo_dane).trim());
        }
      });
    }

    const danesList = Array.from(danesSet);
    console.log(`📍 Ubicación: ${municipio}, ${departamento} (DANE: ${codigo_dane})`);
    if (danesList.length > 1) {
      console.log(`📍 Incluyendo municipios adyacentes para validación: ${danesList.join(', ')}`);
    }

    // 4. Obtener TODAS las mediciones de la campaña
    console.log(`📊 Fetching ALL spectrum data for campaign ${campaignId}, sensor ${sensorMac}...`);
    
    const spectrumData = await query(`
      SELECT 
        pxx, 
        start_freq_hz, 
        end_freq_hz, 
        "timestamp",
        excursion_peak_to_peak_hz,
        excursion_peak_deviation_hz,
        excursion_rms_deviation_hz,
        depth_peak_to_peak,
        depth_peak_deviation,
        depth_rms_deviation,
        lat,
        lng
      FROM sensor_data
      WHERE mac = $1 
        AND campaign_id = $2
      ORDER BY "timestamp" ASC
    `, [sensorMac, campaignId]);

    if (spectrumData.rows.length === 0) {
      return res.status(404).json({ 
        error: 'No spectrum data found for campaign',
        details: `No se encontraron datos espectrales para la campaña ${campaign.name}`
      });
    }

    console.log(`✅ Found ${spectrumData.rows.length} spectrum measurements - Processing all...`);

    // 5. Configuración de análisis
    // UMBRAL_DB ya definido al inicio
    
    // Obtener tolerancias del sistema
    let delta_fc_khz = 100; // Valor por defecto
    let delta_bw_khz = 10;  // Valor por defecto
    
    try {
      const configResult = await query(`
        SELECT key, value FROM system_configurations 
        WHERE key IN ('center_freq_tolerance_khz', 'bandwidth_tolerance_khz')
      `);
      
      configResult.rows.forEach(row => {
        if (row.key === 'center_freq_tolerance_khz') delta_fc_khz = parseFloat(row.value);
        if (row.key === 'bandwidth_tolerance_khz') delta_bw_khz = parseFloat(row.value);
      });
      console.log(`⚙️ Using system tolerances: FC=${delta_fc_khz}kHz, BW=${delta_bw_khz}kHz`);
    } catch (configError) {
      console.warn('⚠️ Could not fetch system configurations, using defaults:', configError);
    }

    const allMediciones: any[] = [];
    let totalEmisionesGlobal = 0;
    let totalAutorizadasGlobal = 0;
    let totalSinLicenciaGlobal = 0;
    let totalCumplenGlobal = 0;
    let totalFueraParametrosGlobal = 0;

    // Helper para parsear un frame de la DB
    const parseFrame = (frameData: any) => {
      let pxxArray: number[];
      try {
        pxxArray = typeof frameData.pxx === 'string'
          ? JSON.parse(frameData.pxx)
          : frameData.pxx;
      } catch {
        return null;
      }
      return {
        pxxArray,
        frame: {
          Pxx: pxxArray,
          start_freq_hz: parseInt(frameData.start_freq_hz),
          end_freq_hz: parseInt(frameData.end_freq_hz),
          timestamp: parseInt(frameData.timestamp),
          excursion: frameData.excursion_peak_to_peak_hz ? {
            unit: 'hz',
            peak_to_peak_hz: parseFloat(frameData.excursion_peak_to_peak_hz),
            peak_deviation_hz: parseFloat(frameData.excursion_peak_deviation_hz),
            rms_deviation_hz: parseFloat(frameData.excursion_rms_deviation_hz)
          } : undefined,
          depth: frameData.depth_peak_to_peak ? {
            unit: 'percent',
            peak_to_peak: parseFloat(frameData.depth_peak_to_peak),
            peak_deviation: parseFloat(frameData.depth_peak_deviation),
            rms_deviation: parseFloat(frameData.depth_rms_deviation)
          } : undefined
        }
      };
    };

    // Helper para formatear el resultado de una emisión
    const formatEmission = (emission: any) => {
      const freqMhz = emission.fc_medida_MHz || (emission.freq_hz ? emission.freq_hz / 1e6 : null);
      const potenciaDbm = emission.p_medida_dBm !== undefined ? emission.p_medida_dBm : emission.power_dbm;
      const bwKhz = emission.bw_medido_kHz || (emission.bw_hz ? emission.bw_hz / 1000 : null);
      const cumpleFC = emission.Cumple_FC;
      const cumpleBW = emission.Cumple_BW;
      const licencia = emission.Licencia;

      let estadoCumplimiento = 'DESCONOCIDO';
      if (licencia === 'SI' && cumpleFC === 'SI' && cumpleBW === 'SI') {
        estadoCumplimiento = 'CUMPLE';
      } else if (licencia === 'NO') {
        estadoCumplimiento = 'SIN_LICENCIA';
      } else if (licencia === 'SI' && (cumpleFC === 'NO' || cumpleBW === 'NO')) {
        estadoCumplimiento = 'FUERA_PARAMETROS';
      }

      return {
        frecuencia_mhz: freqMhz,
        potencia_dbm: potenciaDbm,
        ancho_banda_khz: bwKhz,
        estado_cumplimiento: estadoCumplimiento,
        cumple_fc: cumpleFC,
        cumple_bw: cumpleBW,
        licencia: licencia,
        dane_asociado: emission._dane_autorizado || codigo_dane,
        fc_nominal_mhz: emission.fc_nominal_MHz,
        delta_f_mhz: emission.delta_f_MHz,
        bw_nominal_khz: emission.bw_nominal_kHz,
        delta_bw_khz: emission.delta_bw_kHz,
        p_nominal_dbm: emission.p_nominal_dBm,
        delta_p_db: emission.delta_p_dB,
        nf_dbm: emission.nf_dbm,
        mer_db: emission.mer_db,
        ber_est: emission.ber_est
      };
    };

    // Construir la lista de frames para el batch
    const parsedFrames = spectrumData.rows.map(parseFrame);

    // Indexar solo los frames válidos manteniendo el índice original
    const validFrames = parsedFrames
      .map((f, i) => ({ parsed: f, originalIndex: i }))
      .filter(x => x.parsed !== null);

    // Dividir en sub-batches para distribuir entre los 4 workers de gunicorn.
    // Cada worker es un proceso separado sin GIL compartido → paralelismo real de CPU.
    const GUNICORN_WORKERS = 4;
    const chunkSize = Math.ceil(validFrames.length / GUNICORN_WORKERS);
    const chunks: (typeof validFrames)[] = [];
    for (let i = 0; i < validFrames.length; i += chunkSize) {
      chunks.push(validFrames.slice(i, i + chunkSize));
    }

    const buildSubBatch = (chunk: typeof validFrames) => ({
      max_workers: 4,
      frames: chunk.map(x => ({
        frame: x.parsed!.frame,
        cumplimiento: 1,
        dane: codigo_dane ? String(codigo_dane).trim() : null,
        danes: danesList,
        picos: [],
        umbral_db: UMBRAL_DB,
        delta_fc_khz: delta_fc_khz,
        delta_bw_khz: delta_bw_khz
      }))
    });

    console.log(`🚀 Sending ${validFrames.length} frames as ${chunks.length} parallel sub-batches (~${chunkSize} frames each) to gunicorn...`);

    // Enviar los sub-batches en paralelo — cada uno va a un worker distinto de gunicorn
    let chunkResponses: any[][];
    try {
      chunkResponses = await Promise.all(
        chunks.map(chunk =>
          axios.post(`${PYTHON_SERVICE_URL}/analyze_batch`, buildSubBatch(chunk), {
            timeout: 3600000,
            headers: { 'Content-Type': 'application/json' }
          }).then(r => r.data.results as any[])
        )
      );
    } catch (batchError: any) {
      console.error('❌ Error calling /analyze_batch:', batchError.message);
      return res.status(503).json({
        error: 'Error en análisis batch Python',
        details: batchError.message
      });
    }

    // Reconstituir resultados en el orden original de los frames
    const batchAnalysisResults: any[] = new Array(parsedFrames.length).fill(null);
    chunks.forEach((chunk, chunkIdx) => {
      const chunkResults = chunkResponses[chunkIdx];
      chunk.forEach((x, localIdx) => {
        batchAnalysisResults[x.originalIndex] = chunkResults?.[localIdx] ?? null;
      });
    });

    console.log(`✅ All ${chunks.length} sub-batches complete. Processing results...`);

    // Procesar cada resultado del batch
    for (let i = 0; i < batchAnalysisResults.length; i++) {
      const analysisResults = batchAnalysisResults[i];
      const parsed = parsedFrames[i];
      if (!parsed || !analysisResults || analysisResults.error) {
        if (analysisResults?.error) {
          console.error(`❌ Error in frame ${i + 1}: ${analysisResults.error}`);
        }
        continue;
      }

      const { pxxArray, frame } = parsed;

      let emissions = analysisResults.results || [];

      if (analysisResults.results_by_dane && danesList.length > 1) {
        for (let k = 0; k < emissions.length; k++) {
          if (emissions[k].Licencia === 'SI') continue;
          for (const d of danesList) {
            const otherResults = analysisResults.results_by_dane[String(d)];
            if (!otherResults) continue;
            const candidate = otherResults[k];
            if (candidate && candidate.Licencia === 'SI') {
              emissions[k] = { ...candidate, _dane_autorizado: d };
              break;
            }
          }
        }
      }

      const emisionesFormateadas = emissions.map(formatEmission);
      const cumplen = emisionesFormateadas.filter((e: any) => e.estado_cumplimiento === 'CUMPLE').length;
      const fueraParametros = emisionesFormateadas.filter((e: any) => e.estado_cumplimiento === 'FUERA_PARAMETROS').length;
      const sinLicencia = emisionesFormateadas.filter((e: any) => e.estado_cumplimiento === 'SIN_LICENCIA').length;
      const autorizadas = cumplen + fueraParametros;

      allMediciones.push({
        timestamp: frame.timestamp,
        fecha_hora: new Date(frame.timestamp).toISOString(),
        num_emisiones: emissions.length,
        emisiones_cumplen: cumplen,
        emisiones_fuera_parametros: fueraParametros,
        emisiones_sin_licencia: sinLicencia,
        emisiones_autorizadas: autorizadas,
        porcentaje_cumplimiento: autorizadas > 0 ? ((cumplen / autorizadas) * 100).toFixed(2) : '0',
        emisiones: emisionesFormateadas,
        datos_tecnicos: {
          puntos_fft: pxxArray.length,
          frecuencia_inicio_hz: frame.start_freq_hz,
          frecuencia_fin_hz: frame.end_freq_hz,
          resolucion_hz: (frame.end_freq_hz - frame.start_freq_hz) / pxxArray.length
        }
      });

      totalEmisionesGlobal += emissions.length;
      totalAutorizadasGlobal += autorizadas;
      totalSinLicenciaGlobal += sinLicencia;
      totalCumplenGlobal += cumplen;
      totalFueraParametrosGlobal += fueraParametros;
    }

    console.log(`✅ Processed ${allMediciones.length} measurements. Total emissions: ${totalEmisionesGlobal}`);

    // Generar reporte final con TODAS las mediciones
    const primeraFecha = allMediciones.length > 0 ? new Date(parseInt(allMediciones[0].timestamp)).toISOString().split('T')[0] : new Date().toISOString().split('T')[0];
    const porcentajeCumplimientoGlobal = totalEmisionesGlobal > 0 
      ? ((totalCumplenGlobal / totalEmisionesGlobal) * 100).toFixed(2)
      : '0';
    
    const report = {
      reporte_automatico: true,
      plataforma: 'Plataforma Convenio 217 de 2025 - ANE',
      fecha_generacion: new Date().toISOString(),
      fecha_medicion: primeraFecha,
      
      campana: {
        id: campaign.id,
        nombre: campaign.name,
        estado: campaign.status,
        fecha_inicio: campaign.start_date,
        fecha_fin: campaign.end_date,
        hora_inicio: campaign.start_time,
        hora_fin: campaign.end_time,
        intervalo_muestreo_s: campaign.interval_seconds,
        rango_frecuencias: {
          inicio_mhz: parseFloat(campaign.start_freq_mhz),
          fin_mhz: parseFloat(campaign.end_freq_mhz),
          ancho_banda_mhz: parseFloat(campaign.bandwidth_mhz),
          resolucion_khz: parseFloat(campaign.resolution_khz)
        }
      },
      
      ubicacion: {
        estacion: `Sensor ${sensorMac}`,
        sensor_mac: sensorMac,
        departamento: departamento,
        municipio: municipio,
        codigo_dane: codigo_dane,
        coordenadas: {
          latitud: latitude,
          longitud: longitude
        }
      },
      
      analisis_espectral: {
        modo: 'compliance',
        cumplimiento_general: totalEmisionesGlobal > 0 && totalCumplenGlobal === totalEmisionesGlobal,
        emisiones_detectadas: totalEmisionesGlobal,
        umbral_db: UMBRAL_DB,
        tolerancia_fc_khz: delta_fc_khz,
        tolerancia_bw_khz: delta_bw_khz,
        correccion_aplicada: false,
        metodo_deteccion: 'Detección automática con umbrales adaptativos (NumPy/SciPy)',
        algoritmo: 'Análisis espectral avanzado con comparación de licencias ANE'
      },
      
      estadisticas: {
        total_mediciones: allMediciones.length,
        total_emisiones: totalEmisionesGlobal,
        emisiones_autorizadas: totalAutorizadasGlobal,
        emisiones_sin_licencia: totalSinLicenciaGlobal,
        emisiones_cumplen: totalCumplenGlobal,
        emisiones_fuera_parametros: totalFueraParametrosGlobal,
        porcentaje_cumplimiento: porcentajeCumplimientoGlobal,
        mediciones_analizadas: spectrumData.rows.length
      },
      
      mediciones: allMediciones,  // TODAS las mediciones con sus emisiones
      
      datos_tecnicos: allMediciones.length > 0 ? {
        primera_medicion: allMediciones[0].timestamp,
        ultima_medicion: allMediciones[allMediciones.length - 1].timestamp,
        total_mediciones: allMediciones.length,
        fecha_hora_medicion: new Date(allMediciones[0].timestamp).toISOString(),
        puntos_fft: allMediciones[0].datos_tecnicos.puntos_fft,
        frecuencia_inicio_hz: allMediciones[0].datos_tecnicos.frecuencia_inicio_hz,
        frecuencia_fin_hz: allMediciones[0].datos_tecnicos.frecuencia_fin_hz,
        resolucion_hz: allMediciones[0].datos_tecnicos.resolucion_hz
      } : null
    };

    console.log(`✅ Report generated. Measurements: ${allMediciones.length}, Total emissions: ${totalEmisionesGlobal}, Compliance: ${porcentajeCumplimientoGlobal}%`);
    
    // 10. Guardar reporte en caché (solo para umbral=5 sin sensor específico)
    if (useCache) {
      try {
        await query(`
          INSERT INTO compliance_reports_cache (campaign_id, report_data, created_at, updated_at)
          VALUES ($1, $2, NOW(), NOW())
          ON CONFLICT (campaign_id) 
          DO UPDATE SET 
            report_data = EXCLUDED.report_data,
            updated_at = NOW()
        `, [campaignId, JSON.stringify(report)]);
        console.log(`💾 Report cached successfully for campaign ${campaignId}`);
      } catch (cacheError) {
        console.error('Error caching report (non-fatal):', cacheError);
        // No fallar si no se puede cachear, solo logear
      }
    } else {
      console.log(`💾 Cache not saved (custom umbral or specific sensor)`);
    }
    
    res.json({
      ...report,
      cached: false,
      freshly_generated: true
    });
    
  } catch (error: any) {
    console.error('Error generating compliance report:', error);
    res.status(500).json({ 
      error: 'Failed to generate report',
      details: error.message 
    });
  }
});

/**
 * @swagger
 * /api/reports/compliance/batch/{campaignId}:
 *   post:
 *     summary: Obtener lista de sensores y estado de reportes para una campaña
 *     description: Devuelve información sobre los sensores de una campaña y sus reportes disponibles
 *     tags: [Reports]
 *     parameters:
 *       - in: path
 *         name: campaignId
 *         required: true
 *         schema:
 *           type: integer
 *         description: ID de la campaña
 *     responses:
 *       200:
 *         description: Lista de sensores y reportes
 *       404:
 *         description: Campaña no encontrada o sin sensores
 *       500:
 *         description: Error obteniendo información
 */
router.post('/compliance/batch/:campaignId', async (req: Request, res: Response) => {
  try {
    const campaignId = parseInt(req.params.campaignId);
    
    console.log(`📋 Getting sensor list and report status for campaign ${campaignId}...`);

    // 1. Verificar que la campaña existe
    const campaignResult = await query(`
      SELECT c.* FROM campaigns c WHERE c.id = $1
    `, [campaignId]);

    if (campaignResult.rows.length === 0) {
      return res.status(404).json({ error: 'Campaign not found' });
    }

    const campaign = campaignResult.rows[0];

    // 2. Obtener todos los sensores de la campaña
    const sensorsResult = await query(`
      SELECT cs.sensor_mac, s.name
      FROM campaign_sensors cs
      LEFT JOIN sensors s ON cs.sensor_mac = s.mac
      WHERE cs.campaign_id = $1
    `, [campaignId]);

    if (sensorsResult.rows.length === 0) {
      return res.status(404).json({ error: 'Campaign has no sensors assigned' });
    }

    const sensors = sensorsResult.rows.map(row => ({
      mac: row.sensor_mac,
      name: row.name || row.sensor_mac
    }));

    console.log(`📡 Found ${sensors.length} sensors`);

    // 3. Devolver información de la campaña y sensores
    res.json({
      campaign_id: campaignId,
      campaign_name: campaign.name,
      total_sensors: sensors.length,
      sensors: sensors,
      message: 'Generate individual reports for each sensor using the /compliance/:campaignId endpoint with sensor_mac parameter'
    });

  } catch (error: any) {
    console.error('Error getting batch report info:', error);
    res.status(500).json({ 
      error: 'Failed to get batch report information',
      details: error.message 
    });
  }
});

export default router;
