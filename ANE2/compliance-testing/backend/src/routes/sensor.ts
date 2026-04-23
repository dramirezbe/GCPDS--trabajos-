import { Router, Request, Response } from 'express';
import { SensorDataModel } from '../models/SensorData';
import { SensorModel } from '../models/Sensor';
import { broadcastToClients, broadcastAudioData } from '../websocket';
import { query } from '../database/connection';

const router = Router();

// ====== Servidor: Auto-stop de monitoreo basado en BD ======
// Garantiza auto-stop aunque el navegador se cierre o el backend se reinicie
// Usa la BD como fuente de verdad (is_monitoring=1, created_at) en lugar de memoria

async function getMonitoringTimeoutMinutes(): Promise<number> {
  try {
    const result = await query(
      `SELECT value FROM system_configurations WHERE key = 'max_monitoring_time_min' LIMIT 1`
    );
    if (result.rows.length > 0) {
      const val = parseInt(result.rows[0].value, 10);
      return isNaN(val) ? 10 : val;
    }
  } catch (e) {
    // Tabla puede no existir aún al arrancar
  }
  return 10; // default 10 minutos
}

async function autoStopExpiredMonitoring() {
  try {
    // Consultar la BD directamente: buscar configs activas de monitoreo
    const timeoutMin = await getMonitoringTimeoutMinutes();
    // created_at es BIGINT (epoch ms), comparar con epoch ms actual
    const cutoffMs = Date.now() - (timeoutMin * 60 * 1000);
    const result = await query(
      `SELECT mac, created_at FROM sensor_configurations 
       WHERE is_active = 1 AND is_monitoring = 1 
       AND created_at < $1`,
      [cutoffMs]
    );

    for (const row of result.rows) {
      const mac = row.mac;
      const createdAtMs = Number(row.created_at);
      const elapsedMin = Math.round((Date.now() - createdAtMs) / 60000);
      console.log(`⏰ Monitoreo expirado para sensor ${mac} (${elapsedMin} min, límite ${timeoutMin} min). Auto-deteniendo...`);
      
      try {
        // 1. Desactivar configuraciones activas
        await query(
          `UPDATE sensor_configurations SET is_active = 0 WHERE mac = $1 AND is_active = 1`,
          [mac]
        );

        // 2. Insertar configuración de stop (freq=0)
        await query(
          `INSERT INTO sensor_configurations (
            mac, start_freq_hz, end_freq_hz, resolution_hz, antenna_port,
            "window", overlap, sample_rate_hz, lna_gain, vga_gain, antenna_amp, is_active
          ) VALUES ($1, 0, 0, 0, 0, 'none', 0, 0, 0, 0, 0, 1)`,
          [mac]
        );

        // 3. Broadcast sensor_configure con freq=0 (para que el sensor físico detenga el escaneo)
        broadcastToClients({
          type: 'sensor_configure',
          data: {
            mac: mac,
            config: {
              center_freq_hz: 0,
              sample_rate_hz: 0,
              resolution_hz: 0,
              antenna_port: 0,
              window: 'hann',
              overlap: 0.5,
              lna_gain: 0,
              vga_gain: 0,
              antenna_amp: false
            },
            timestamp: Date.now()
          }
        });

        // 4. Broadcast sensor_stop (para notificar al frontend)
        broadcastToClients({
          type: 'sensor_stop',
          data: { mac, timestamp: Date.now(), reason: 'monitoring_timeout' }
        });

        // 5. Actualizar estado del sensor a online
        await SensorModel.updateStatus(mac, 'online');
        console.log(`✅ Sensor ${mac} auto-detenido y cambiado a ONLINE (timeout monitoreo: ${timeoutMin} min)`);
      } catch (err) {
        console.error(`❌ Error auto-deteniendo monitoreo para ${mac}:`, err);
      }
    }
  } catch (err) {
    // Silenciar errores de conexión durante el arranque
    // (la BD puede no estar lista aún)
  }
}

// Verificar cada 15 segundos si hay monitoreos expirados
setInterval(autoStopExpiredMonitoring, 15000);
console.log('🔄 Auto-stop de monitoreo activo (basado en BD, cada 15s)');

/**
 * @swagger
 * /api/sensor/status:
 *   post:
 *     summary: Recibir estado del sensor
 *     description: Endpoint para que los sensores físicos envíen su estado (batería, temperatura, calidad de señal)
 *     tags: [Sensor Data]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             $ref: '#/components/schemas/SensorStatus'
 *           example:
 *             mac: "00:11:22:33:44:55"
 *             battery: 85.5
 *             temperature: 28.5
 *             signal_quality: 92.3
 *             timestamp: 1702745000000
 *     responses:
 *       200:
 *         description: Estado recibido correctamente
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Success'
 *       400:
 *         description: Error en los datos enviados
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
router.post('/status', async (req: Request, res: Response) => {
  try {
    const body = req.body;
    
    // Convertir formato antiguo (flat) a nuevo formato (nested) si es necesario
    let status: any;
    if (body.metrics && body.metrics.cpu) {
      // Formato nuevo: ya tiene metrics.cpu como array
      status = body;
    } else if (body.cpu_0 !== undefined) {
      // Formato antiguo: cpu_0, cpu_1, etc. en el nivel raíz
      status = {
        mac: body.mac,
        device_id: body.device_id,
        metrics: {
          cpu: [
            body.cpu_0 || 0,
            body.cpu_1 || 0,
            body.cpu_2 || 0,
            body.cpu_3 || 0
          ],
          ram_mb: body.ram_mb,
          swap_mb: body.swap_mb,
          disk_mb: body.disk_mb,
          temp_c: body.temp_c
        },
        total_metrics: {
          ram_mb: body.total_ram_mb,
          swap_mb: body.total_swap_mb,
          disk_mb: body.total_disk_mb
        },
        delta_t_ms: body.delta_t_ms,
        ping_ms: body.ping_ms,
        timestamp_ms: body.timestamp_ms,
        last_kal_ms: body.last_kal_ms,
        last_ntp_ms: body.last_ntp_ms,
        logs: body.logs
      };
    } else {
      throw new Error('Invalid status format: missing cpu metrics');
    }
    
    // Guardar status en DB
    await SensorDataModel.saveStatus(status);
    
    // Lógica mejorada para actualizar el estado del sensor
    // 1. Obtener el sensor actual para verificar su estado
    let mac = status.mac;
    
    if (!mac && status.device_id) {
      const sensorResult = await query('SELECT mac FROM sensors WHERE id = $1', [status.device_id]);
      if (sensorResult.rows.length > 0) {
        mac = sensorResult.rows[0].mac;
      }
    }

    if (mac) {
      const currentSensor = await SensorModel.getByMac(mac);
      
      if (currentSensor) {
        // Verificar si hay errores en los logs
        const hasError = status.logs && (status.logs.includes('ERROR') || status.logs.includes('CRITICAL'));
        
        if (hasError) {
          // Si hay errores, marcar como error inmediatamente
          // Solo crear alerta si el estado cambió a error
          if (currentSensor.status !== 'error') {
            await SensorModel.updateStatus(mac, 'error');
            console.log(`❌ Sensor ${mac} reported ERROR status via logs`);
            
            // Crear alerta de error crítico
            const SensorHistoryAlertModel = (await import('../models/SensorHistoryAlert')).SensorHistoryAlertModel;
            await SensorHistoryAlertModel.create({
              sensor_mac: mac,
              alert_type: 'Error Crítico',
              description: 'Sensor entró en estado de error debido a errores críticos en los logs',
              timestamp: Date.now()
            });
          } else {
            await SensorModel.updateStatus(mac, 'error');
          }
        } else if (currentSensor.status === 'busy') {
          // Si está ocupado, MANTENER estado busy pero actualizar timestamp (heartbeat)
          await SensorModel.updateStatus(mac, 'busy');
          // console.log(`Sensor ${mac} heartbeat (BUSY)`);
        } else {
          // Funcionamiento normal
          await SensorModel.updateStatus(mac, 'online');
        }
      }
    }
    
    // Broadcast a clientes WebSocket
    broadcastToClients({
      type: 'sensor_status',
      data: status
    });
    
    res.status(200).json({ success: true, message: 'Status received' });
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensor/gps:
 *   post:
 *     summary: Recibir ubicación GPS del sensor
 *     description: Endpoint para que los sensores físicos envíen su ubicación GPS
 *     tags: [Sensor Data]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             $ref: '#/components/schemas/SensorGPS'
 *           example:
 *             mac: "00:11:22:33:44:55"
 *             lat: 4.711
 *             lng: -74.0721
 *             alt: 2640
 *             timestamp: 1702745000000
 *     responses:
 *       200:
 *         description: Datos GPS recibidos correctamente
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Success'
 *       400:
 *         description: Error en los datos GPS
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
router.post('/gps', async (req: Request, res: Response) => {
  try {
    const gps = req.body;
    
    // Guardar GPS en DB
    await SensorDataModel.saveGPS(gps);
    
    // Actualizar ubicación del sensor
    await SensorModel.updateLocation(gps.mac, gps.lat, gps.lng, gps.alt);
    
    // Broadcast a clientes WebSocket
    broadcastToClients({
      type: 'sensor_gps',
      data: gps
    });
    
    res.status(200).json({ success: true, message: 'GPS data received' });
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensor/data:
 *   post:
 *     summary: Recibir datos de espectro del sensor
 *     description: |
 *       Endpoint principal para que los sensores envíen datos de espectro radioeléctrico (FFT, potencias, métricas de modulación).
 *       Los datos son almacenados en la base de datos y transmitidos en tiempo real vía WebSocket.
 *     tags: [Sensor Data]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             $ref: '#/components/schemas/SensorData'
 *           example:
 *             mac: "00:11:22:33:44:55"
 *             Pxx: [-80.5, -82.3, -79.1, -81.2]
 *             start_freq_hz: 88000000
 *             end_freq_hz: 108000000
 *             timestamp: 1702745000000
 *             excursion: 75000
 *             depth: 0.85
 *             lat: 4.711
 *             lng: -74.0721
 *             campaign_id: 1
 *     responses:
 *       200:
 *         description: Datos de espectro recibidos correctamente
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Success'
 *       400:
 *         description: Error en los datos de espectro
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
router.post('/data', async (req: Request, res: Response) => {
  try {
    const data = req.body;
    // Estructura esperada: mac, campaign_id (opcional), Pxx, start_freq_hz, end_freq_hz, timestamp,
    // excursion {unit, peak_to_peak_hz, peak_deviation_hz, rms_deviation_hz} (opcional),
    // depth {unit, peak_to_peak, peak_deviation, rms_deviation} (opcional)
    
    // FIX: Si no viene campaign_id, intentar deducirlo buscando una campaña activa para este sensor
    // Validando que los parámetros de frecuencia coincidan para no mezclar datos de monitoreo en tiempo real
    if (!data.campaign_id) {
      try {
        const activeCampaignResult = await query(`
          SELECT c.id, c.start_freq_mhz, c.end_freq_mhz 
          FROM campaigns c
          INNER JOIN campaign_sensors cs ON c.id = cs.campaign_id
          WHERE cs.sensor_mac = $1 
            AND c.status = 'running'
          LIMIT 1
        `, [data.mac]);
        
        if (activeCampaignResult.rows.length > 0) {
          const campaign = activeCampaignResult.rows[0];
          
          // Validar frecuencias para evitar asociar datos de monitoreo manual
          // Convertir MHz a Hz y permitir pequeña tolerancia (5 kHz para ser más robusto ante redondeos)
          const campaignStartHz = Math.round(parseFloat(campaign.start_freq_mhz) * 1e6);
          const campaignEndHz = Math.round(parseFloat(campaign.end_freq_mhz) * 1e6);
          const TOLERANCE_HZ = 5000; // 5 kHz de tolerancia
          
          const startDiff = Math.abs((data.start_freq_hz || 0) - campaignStartHz);
          const endDiff = Math.abs((data.end_freq_hz || 0) - campaignEndHz);
          
          if (startDiff <= TOLERANCE_HZ && endDiff <= TOLERANCE_HZ) {
            data.campaign_id = campaign.id;
            console.log(`🔍 Inferred campaign_id ${data.campaign_id} for sensor ${data.mac} (Freq Match: start diff ${startDiff}Hz, end diff ${endDiff}Hz)`);
          } else {
            console.log(`⚠️ Sensor ${data.mac} sent data during running campaign ${campaign.id} but frequencies mismatch. Ignoring association.`);
            console.log(`   Campaign: ${campaignStartHz}-${campaignEndHz} Hz`);
            console.log(`   Data:     ${data.start_freq_hz}-${data.end_freq_hz} Hz`);
            console.log(`   Diffs:    Start ${startDiff}Hz, End ${endDiff}Hz (Tolerance: ${TOLERANCE_HZ}Hz)`);
          }
        }
      } catch (err) {
        console.error('Error inferring campaign_id:', err);
      }
    }

    // Verificar si el sensor está en modo monitoreo (NO guardar datos)
    const activeConfig = await SensorDataModel.getActiveConfiguration(data.mac);
    const isMonitoring = activeConfig?.is_monitoring;

    // SIEMPRE actualizar el cache en memoria para visualización en tiempo real (polling)
    SensorDataModel.updateCache(data);

    if (!isMonitoring) {
      // Guardar datos en DB (solo si NO es monitoreo)
      await SensorDataModel.saveData(data);
    } else {
      // Si es monitoreo, solo loguear ocasionalmente para debug
      if (Math.random() < 0.01) {
        console.log(`📡 Sensor ${data.mac} in Monitoring Mode - Data NOT saved to DB`);
      }
    }
    
    // Preparar datos para broadcast
    const broadcastData: any = {
      type: 'sensor_data',
      data: {
        mac: data.mac,
        Pxx: data.Pxx,
        start_freq_hz: data.start_freq_hz,
        end_freq_hz: data.end_freq_hz,
        timestamp: data.timestamp
      }
    };
    
    // Incluir campaign_id si está presente
    if (data.campaign_id) {
      broadcastData.data.campaign_id = data.campaign_id;
    }
    
    // Incluir métricas de demodulación si están presentes (con estructura completa)
    if (data.excursion) {
      broadcastData.data.excursion = data.excursion;
    }
    if (data.depth) {
      broadcastData.data.depth = data.depth;
    }
    
    // Broadcast a clientes WebSocket para visualización en tiempo real
    broadcastToClients(broadcastData);
    
    res.status(200).json({ success: true, message: 'Data received' });
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensor/{mac}/latest-status:
 *   get:
 *     summary: Obtener último estado del sensor
 *     description: Consulta el último estado reportado por un sensor específico
 *     tags: [Sensor Query]
 *     parameters:
 *       - in: path
 *         name: mac
 *         required: true
 *         schema:
 *           type: string
 *         description: Dirección MAC del sensor
 *         example: "00:11:22:33:44:55"
 *     responses:
 *       200:
 *         description: Estado del sensor
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/SensorStatus'
 *       404:
 *         description: No se encontraron datos de estado
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *       500:
 *         description: Error del servidor
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
router.get('/:mac/latest-status', async (req: Request, res: Response) => {
  try {
    const status = await SensorDataModel.getLatestStatus(req.params.mac);
    if (!status) {
      return res.status(404).json({ error: 'No status data found' });
    }
    res.json(status);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensor/{mac}/latest-gps:
 *   get:
 *     summary: Obtener última ubicación GPS del sensor
 *     description: Consulta la última ubicación GPS reportada por un sensor específico
 *     tags: [Sensor Query]
 *     parameters:
 *       - in: path
 *         name: mac
 *         required: true
 *         schema:
 *           type: string
 *         description: Dirección MAC del sensor
 *         example: "00:11:22:33:44:55"
 *     responses:
 *       200:
 *         description: Ubicación GPS del sensor
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/SensorGPS'
 *       404:
 *         description: No se encontraron datos GPS
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
router.get('/:mac/latest-gps', async (req: Request, res: Response) => {
  try {
    const gps = await SensorDataModel.getLatestGPS(req.params.mac);
    if (!gps) {
      return res.status(404).json({ error: 'No GPS data found' });
    }
    res.json(gps);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensor/{mac}/latest-data:
 *   get:
 *     summary: Obtener últimos datos de espectro del sensor
 *     description: Consulta los últimos N datos de espectro capturados por un sensor
 *     tags: [Sensor Query]
 *     parameters:
 *       - in: path
 *         name: mac
 *         required: true
 *         schema:
 *           type: string
 *         description: Dirección MAC del sensor
 *         example: "00:11:22:33:44:55"
 *       - in: query
 *         name: limit
 *         schema:
 *           type: integer
 *           default: 100
 *         description: Número máximo de registros a devolver
 *         example: 50
 *     responses:
 *       200:
 *         description: Array de datos de espectro
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 $ref: '#/components/schemas/SensorData'
 *       500:
 *         description: Error del servidor
 */
router.get('/:mac/latest-data', async (req: Request, res: Response) => {
  try {
    const limit = Number(req.query.limit) || 100;
    const data = await SensorDataModel.getLatestData(req.params.mac, limit);
    res.json(data);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensor/{mac}/data/range:
 *   get:
 *     summary: Obtener datos de espectro por rango de tiempo
 *     description: Consulta datos de espectro de un sensor en un rango de tiempo específico
 *     tags: [Sensor Query]
 *     parameters:
 *       - in: path
 *         name: mac
 *         required: true
 *         schema:
 *           type: string
 *         description: Dirección MAC del sensor
 *         example: "00:11:22:33:44:55"
 *       - in: query
 *         name: start
 *         required: true
 *         schema:
 *           type: integer
 *         description: Timestamp Unix inicial (ms)
 *         example: 1702745000000
 *       - in: query
 *         name: end
 *         required: true
 *         schema:
 *           type: integer
 *         description: Timestamp Unix final (ms)
 *         example: 1702831400000
 *     responses:
 *       200:
 *         description: Array de datos de espectro en el rango especificado
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 $ref: '#/components/schemas/SensorData'
 *       400:
 *         description: Parámetros inválidos
 */
router.get('/:mac/data/range', async (req: Request, res: Response) => {
  try {
    const startTime = Number(req.query.start);
    const endTime = Number(req.query.end);
    
    if (!startTime || !endTime) {
      return res.status(400).json({ error: 'start and end query parameters are required' });
    }
    
    const data = await SensorDataModel.getDataByTimeRange(req.params.mac, startTime, endTime);
    res.json(data);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensor/{mac}/configure:
 *   post:
 *     summary: Configurar sensor e iniciar escaneo
 *     description: |
 *       Envía configuración de escaneo a un sensor específico y arranca la adquisición de datos.
 *       La configuración se transmite vía WebSocket al sensor físico.
 *       
 *       **NUEVO FORMATO (compatible con JSON actualizado):**
 *       - ❌ Campo `span` eliminado (usar solo `sample_rate_hz`)
 *       - ✅ `demodulation` puede ser string simple ("am", "fm") o null
 *       - ✅ `filter` usa `{start_freq_hz, end_freq_hz}` para rangos de frecuencia
 *       - ✅ Mantiene retrocompatibilidad con formato antiguo
 *     tags: [Sensor Control]
 *     parameters:
 *       - in: path
 *         name: mac
 *         required: true
 *         schema:
 *           type: string
 *         description: Dirección MAC del sensor
 *         example: "00:11:22:33:44:55"
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - center_frequency
 *               - sample_rate_hz
 *               - resolution_hz
 *               - antenna_port
 *             properties:
 *               mac:
 *                 type: string
 *                 example: "00:11:22:33:44:55"
 *               center_frequency:
 *                 type: number
 *                 description: Frecuencia central en Hz
 *                 example: 97500000
 *               sample_rate_hz:
 *                 type: number
 *                 description: Tasa de muestreo en Hz (reemplaza span)
 *                 example: 20000000
 *               resolution_hz:
 *                 type: number
 *                 description: Resolution Bandwidth en Hz
 *                 example: 100000
 *               vbw:
 *                 type: string
 *                 description: Video Bandwidth
 *                 example: "auto"
 *               antenna_port:
 *                 type: number
 *                 description: Puerto de antena (1-4)
 *                 example: 1
 *               window:
 *                 type: string
 *                 example: "hann"
 *               overlap:
 *                 type: number
 *                 example: 0.5
 *               lna_gain:
 *                 type: number
 *                 example: 0
 *               vga_gain:
 *                 type: number
 *                 example: 0
 *               antenna_amp:
 *                 type: boolean
 *                 example: true
 *               demodulation:
 *                 type: string
 *                 nullable: true
 *                 description: Tipo de demodulación (NUEVO FORMATO string simple)
 *                 example: "fm"
 *               filter:
 *                 type: object
 *                 nullable: true
 *                 description: Filtro de frecuencias (NUEVO FORMATO)
 *                 properties:
 *                   start_freq_hz:
 *                     type: number
 *                   end_freq_hz:
 *                     type: number
 *           example:
 *             mac: "00:11:22:33:44:55"
 *             center_frequency: 97500000
 *             sample_rate_hz: 20000000
 *             resolution_hz: 100000
 *             vbw: "auto"
 *             antenna_port: 1
 *             window: "hann"
 *             overlap: 0.5
 *             lna_gain: 0
 *             vga_gain: 0
 *             antenna_amp: true
 *             demodulation: "fm"
 *             filter:
 *               start_freq_hz: 87500000
 *               end_freq_hz: 107500000
 *     responses:
 *       200:
 *         description: Configuración enviada exitosamente
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 success:
 *                   type: boolean
 *                   example: true
 *                 message:
 *                   type: string
 *                   example: Configuration sent to sensor
 *                 sensor:
 *                   type: string
 *                   example: Sensor Simulado
 *                 mac:
 *                   type: string
 *                   example: "00:11:22:33:44:55"
 *                 config:
 *                   type: object
 *       404:
 *         description: Sensor no encontrado
 *       400:
 *         description: Error en la configuración
 */
router.post('/:mac/configure', async (req: Request, res: Response) => {
  try {
    const mac = req.params.mac;
    const scanConfig = req.body;
    
    // ===== TEST: LOG DETALLADO DE DATOS RECIBIDOS =====
    console.log('\n╔════════════════════════════════════════════════════════╗');
    console.log('║  CONFIGURACIÓN RECIBIDA EN BACKEND - TEST FILTRO      ║');
    console.log('╚════════════════════════════════════════════════════════╝');
    console.log('📥 Sensor MAC:', mac);
    console.log('📊 Datos completos recibidos:');
    console.log(JSON.stringify(scanConfig, null, 2));
    console.log('\n🔍 Análisis específico del filtro:');
    console.log('  • filterEnabled en frontend envió propiedad "filter":', scanConfig.filter !== undefined);
    if (scanConfig.filter) {
      console.log('  • Filtro start_freq_hz:', scanConfig.filter.start_freq_hz, 'Hz →', (scanConfig.filter.start_freq_hz / 1e6).toFixed(2), 'MHz');
      console.log('  • Filtro end_freq_hz:', scanConfig.filter.end_freq_hz, 'Hz →', (scanConfig.filter.end_freq_hz / 1e6).toFixed(2), 'MHz');
    } else {
      console.log('  • ✅ NO se recibió filtro (correcto si está deshabilitado)');
    }
    console.log('═══════════════════════════════════════════════════════\n');
    // ===== FIN TEST =====
    
    // Verificar que el sensor existe
    const sensor = await SensorModel.getByMac(mac);
    if (!sensor) {
      return res.status(404).json({ error: 'Sensor not found' });
    }

    // Guardar configuración en la base de datos (NUEVO FORMATO - compatible con JSON actualizado)
    const configToSave: any = {
      mac: mac,
      center_frequency: scanConfig.center_frequency,
      sample_rate_hz: scanConfig.sample_rate_hz,
      resolution_hz: scanConfig.resolution_hz,
      antenna_port: scanConfig.antenna_port,
      window: scanConfig.window || 'hann',
      overlap: scanConfig.overlap || 0.5,
      lna_gain: scanConfig.lna_gain || 0,
      vga_gain: scanConfig.vga_gain || 0,
      antenna_amp: scanConfig.antenna_amp !== false,
      is_monitoring: scanConfig.is_monitoring === true
    };

    // Agregar demodulación si está presente (nuevo formato: string simple)
    if (scanConfig.demodulation) {
      // Nuevo formato: demodulation es un string ("am", "fm") o null
      if (typeof scanConfig.demodulation === 'string') {
        configToSave.demod_type = scanConfig.demodulation.toUpperCase();
      } 
      // Mantener compatibilidad con formato antiguo (objeto)
      else if (typeof scanConfig.demodulation === 'object') {
        configToSave.demodulation = {
          type: scanConfig.demodulation.type,
          bandwidth_hz: scanConfig.demodulation.bw_hz,
          center_freq_hz: scanConfig.demodulation.center_freq_hz,
          with_metrics: scanConfig.demodulation.with_metrics,
          port_socket: scanConfig.demodulation.port_socket
        };
      }
    }

    // Agregar filtros si están presentes (nuevo formato: start_freq_hz y end_freq_hz)
    if (scanConfig.filter) {
      if (scanConfig.filter.start_freq_hz && scanConfig.filter.end_freq_hz) {
        // Nuevo formato: filtro por rangos de frecuencia
        // CORRECCIÓN: Guardar en campos de filtro específicos, no en rango de escaneo
        configToSave.filter_start_freq_hz = scanConfig.filter.start_freq_hz;
        configToSave.filter_end_freq_hz = scanConfig.filter.end_freq_hz;
      } 
      // Mantener compatibilidad con formato antiguo (tipo de filtro)
      else if (scanConfig.filter.type) {
        configToSave.filter = {
          type: scanConfig.filter.type,
          bw_hz: scanConfig.filter.bw_hz,
          order: scanConfig.filter.order
        };
      }
    }
    
    await SensorDataModel.saveConfiguration(configToSave);
    
    // Preparar configuración para enviar al sensor físico
    // Convertir campos del frontend al formato que espera el sensor
    const sensorConfig: any = {
      ...scanConfig,
      // El sensor espera center_freq_hz, pero el frontend puede enviar center_frequency
      center_freq_hz: scanConfig.center_freq_hz || scanConfig.center_frequency,
      // Remover center_frequency para evitar confusión
      center_frequency: undefined
    };
    
    // En un sistema real, aquí se enviaría la configuración al sensor físico
    // Por ahora, solo broadcast por WebSocket para que el sensor la reciba
    broadcastToClients({
      type: 'sensor_configure',
      data: {
        mac: mac,
        config: sensorConfig,
        timestamp: Date.now()
      }
    });
    
    // Si no es un comando de parada (center_freq_hz != 0), actualizar estado a 'busy'
    if (scanConfig.center_frequency !== 0) {
      await SensorModel.updateStatus(mac, 'busy');
      console.log(`⚡ Sensor ${mac} updated to BUSY status (Acquisition Started)`);
      
      // Si es monitoreo, el auto-stop se maneja por BD (is_monitoring=1, created_at)
      if (scanConfig.is_monitoring) {
        console.log(`⏱️ Monitoreo iniciado para ${mac}: auto-stop controlado por BD (is_monitoring=1)`);
      }
    } else {
      // Si es un comando de parada, actualizar estado a 'online'
      await SensorModel.updateStatus(mac, 'online');
      console.log(`⚡ Sensor ${mac} updated to ONLINE status (Acquisition Stopped)`);
    }
    
    console.log(`📡 Configuración enviada al sensor ${mac}:`, sensorConfig);
    
    res.status(200).json({ 
      success: true, 
      message: 'Configuration sent to sensor',
      sensor: sensor.name,
      mac: mac,
      config: scanConfig
    });
  } catch (error: any) {
    console.error('Error configuring sensor:', error);
    res.status(400).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensor/{mac}/stop:
 *   post:
 *     summary: Detener adquisición del sensor
 *     description: Envía comando para detener la adquisición de datos en un sensor específico
 *     tags: [Sensor Control]
 *     parameters:
 *       - in: path
 *         name: mac
 *         required: true
 *         schema:
 *           type: string
 *         description: Dirección MAC del sensor
 *         example: "00:11:22:33:44:55"
 *     responses:
 *       200:
 *         description: Comando de detención enviado
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 success:
 *                   type: boolean
 *                 message:
 *                   type: string
 *                 sensor:
 *                   type: string
 *                 mac:
 *                   type: string
 *       404:
 *         description: Sensor no encontrado
 */
router.post('/:mac/stop', async (req: Request, res: Response) => {
  try {
    const mac = req.params.mac;
    
    // Verificar que el sensor existe
    const sensor = await SensorModel.getByMac(mac);
    if (!sensor) {
      return res.status(404).json({ error: 'Sensor not found' });
    }

    // Desactivar todas las configuraciones activas para este sensor
    await query(
      `UPDATE sensor_configurations SET is_active = 0 WHERE mac = $1 AND is_active = 1`,
      [mac]
    );
    
    // Crear configuración de "stop" con center_freq_hz en 0
    // Esto le indica al sensor que debe detener la adquisición
    await query(
      `INSERT INTO sensor_configurations (
        mac, start_freq_hz, end_freq_hz, resolution_hz, antenna_port, 
        "window", overlap, sample_rate_hz, lna_gain, vga_gain, antenna_amp, is_active
      ) VALUES ($1, 0, 0, 0, 0, 'none', 0, 0, 0, 0, 0, 1)`,
      [mac]
    );
    
    console.log(`🛑 Configuración de STOP guardada para sensor ${mac} (center_freq_hz = 0)`);
    
    // Broadcast por WebSocket (opcional, para notificar frontend en tiempo real)
    broadcastToClients({
      type: 'sensor_stop',
      data: {
        mac: mac,
        timestamp: Date.now()
      }
    });
    
    // Actualizar estado a 'online'
    await SensorModel.updateStatus(mac, 'online');
    console.log(`⚡ Sensor ${mac} updated to ONLINE status (Acquisition Stopped via /stop)`);

    res.status(200).json({ 
      success: true, 
      message: 'Stop command sent to sensor',
      sensor: sensor.name,
      mac: mac
    });
  } catch (error: any) {
    console.error('Error stopping sensor:', error);
    res.status(400).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensor/{mac}/configuration:
 *   post:
 *     summary: Guardar configuración del sensor
 *     description: Almacena una configuración de escaneo para un sensor
 *     tags: [Sensor Control]
 *     parameters:
 *       - in: path
 *         name: mac
 *         required: true
 *         schema:
 *           type: string
 *         description: Dirección MAC del sensor
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             $ref: '#/components/schemas/ScanConfiguration'
 *     responses:
 *       201:
 *         description: Configuración guardada
 *       400:
 *         description: Error en los datos
 */
router.post('/:mac/configuration', async (req: Request, res: Response) => {
  try {
    const config = {
      mac: req.params.mac,
      ...req.body
    };
    const result = await SensorDataModel.saveConfiguration(config);
    res.status(201).json(result);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensor/{mac}/configuration:
 *   get:
 *     summary: Obtener configuración activa del sensor
 *     description: |
 *       Consulta la configuración de escaneo actualmente activa para un sensor.
 *       Los sensores pueden usar este endpoint para obtener su configuración (similar a GET-realtime.json).
 *     tags: [Sensor Query]
 *     parameters:
 *       - in: path
 *         name: mac
 *         required: true
 *         schema:
 *           type: string
 *         description: Dirección MAC del sensor
 *         example: "00:11:22:33:44:55"
 *     responses:
 *       200:
 *         description: Configuración activa
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/ScanConfiguration'
 *       404:
 *         description: No se encontró configuración activa
 */
router.get('/:mac/configuration', async (req: Request, res: Response) => {
  try {
    const config = await SensorDataModel.getActiveConfiguration(req.params.mac);
    if (!config) {
      return res.status(404).json({ error: 'No active configuration found' });
    }
    res.json(config);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensor/audio:
 *   post:
 *     summary: Recibir audio demodulado del sensor
 *     description: |
 *       Endpoint para recibir audio demodulado (AM/FM) desde los sensores.
 *       El audio se transmite en tiempo real a los clientes WebSocket suscritos.
 *     tags: [Sensor Data]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             $ref: '#/components/schemas/SensorAudio'
 *           example:
 *             mac: "00:11:22:33:44:55"
 *             audio: [0.1, 0.15, -0.2, 0.05, -0.1]
 *             demodType: "FM"
 *             timestamp: 1702745000000
 *     responses:
 *       200:
 *         description: Audio recibido y transmitido
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Success'
 *       400:
 *         description: Datos de audio inválidos
 */
router.post('/audio', async (req: Request, res: Response) => {
  try {
    const { mac, audio, demodType, timestamp } = req.body;
    
    if (!audio || !demodType) {
      return res.status(400).json({ error: 'Missing audio data or demodType' });
    }
    
    // Broadcast audio a suscriptores WebSocket
    broadcastAudioData(audio, demodType);
    
    console.log(`🎵 Audio ${demodType} received from ${mac} and broadcasted`);
    
    res.status(200).json({ success: true, message: 'Audio received and broadcasted' });
  } catch (error: any) {
    console.error('Error processing audio:', error);
    res.status(400).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensor/{mac}/campaigns:
 *   get:
 *     summary: Obtener campañas asignadas a un sensor
 *     description: |
 *       Endpoint para que los sensores obtengan la lista de campañas asignadas.
 *       Estructura compatible con GET-campaigns.jsonc del sensor (NUEVO FORMATO).
 *       
 *       **Cambios en el nuevo formato:**
 *       - ❌ Campo `span` eliminado (redundante con `sample_rate_hz`)
 *       - ❌ Campo `scale` eliminado
 *       - ✅ `filter` ahora usa `{start_freq_hz, end_freq_hz}` basado en rangos de la campaña
 *     tags: [Sensor Query]
 *     parameters:
 *       - in: path
 *         name: mac
 *         required: true
 *         schema:
 *           type: string
 *         description: Dirección MAC del sensor
 *         example: "00:11:22:33:44:55"
 *       - in: query
 *         name: status
 *         schema:
 *           type: string
 *           enum: [scheduled, running, completed, cancelled]
 *         description: Filtrar por estado de campaña (opcional)
 *     responses:
 *       200:
 *         description: Lista de campañas en formato esperado por el sensor (NUEVO FORMATO)
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 campaigns:
 *                   type: array
 *                   items:
 *                     type: object
 *                     properties:
 *                       campaign_id:
 *                         type: number
 *                         example: 1
 *                       status:
 *                         type: string
 *                         example: "scheduled"
 *                       center_freq_hz:
 *                         type: number
 *                         example: 97500000
 *                       rbw_hz:
 *                         type: number
 *                         example: 10000
 *                       sample_rate_hz:
 *                         type: number
 *                         description: Tasa de muestreo (reemplaza span)
 *                         example: 20000000
 *                       antenna_port:
 *                         type: number
 *                         example: 1
 *                       acquisition_period_s:
 *                         type: number
 *                         example: 300
 *                       window:
 *                         type: string
 *                         example: "hamming"
 *                       overlap:
 *                         type: number
 *                         example: 0.5
 *                       lna_gain:
 *                         type: number
 *                         example: 0
 *                       vga_gain:
 *                         type: number
 *                         example: 0
 *                       antenna_amp:
 *                         type: boolean
 *                         example: false
 *                       timeframe:
 *                         type: object
 *                         properties:
 *                           start:
 *                             type: number
 *                             nullable: true
 *                           end:
 *                             type: number
 *                             nullable: true
 *                       filter:
 *                         type: object
 *                         nullable: true
 *                         description: Filtro con rangos de frecuencia (NUEVO FORMATO)
 *                         properties:
 *                           start_freq_hz:
 *                             type: number
 *                           end_freq_hz:
 *                             type: number
 *             example:
 *               campaigns:
 *                 - campaign_id: 1
 *                   status: "scheduled"
 *                   center_freq_hz: 97500000
 *                   rbw_hz: 10000
 *                   sample_rate_hz: 20000000
 *                   antenna_port: 1
 *                   acquisition_period_s: 300
 *                   window: "hamming"
 *                   overlap: 0.5
 *                   lna_gain: 0
 *                   vga_gain: 0
 *                   antenna_amp: false
 *                   timeframe:
 *                     start: 1704067200000
 *                     end: 1704672000000
 *                   filter:
 *                     start_freq_hz: 87500000
 *                     end_freq_hz: 107500000
 *       404:
 *         description: Sensor no encontrado
 *       500:
 *         description: Error del servidor
 */
// DEBUG endpoint temporal
router.get('/:mac/campaigns-debug', async (req: Request, res: Response) => {
  try {
    const mac = req.params.mac;
    const result = await query(`
      SELECT c.id, c.name, c.start_freq_mhz, c.end_freq_mhz, c.config 
      FROM campaigns c
      INNER JOIN campaign_sensors cs ON c.id = cs.campaign_id
      WHERE cs.sensor_mac = $1
      LIMIT 2
    `, [mac]);
    
    const debug = result.rows.map((c: any) => ({
      id: c.id,
      name: c.name,
      start_freq_mhz: c.start_freq_mhz,
      start_freq_type: typeof c.start_freq_mhz,
      end_freq_mhz: c.end_freq_mhz,
      end_freq_type: typeof c.end_freq_mhz,
      config_raw: c.config,
      config_type: typeof c.config,
      config_parsed: typeof c.config === 'string' ? JSON.parse(c.config) : c.config
    }));
    
    res.json({ debug });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

router.get('/:mac/campaigns', async (req: Request, res: Response) => {
  try {
    const mac = req.params.mac;
    const statusFilter = req.query.status as string;
    
    // Verificar que el sensor existe
    const sensor = await SensorModel.getByMac(mac);
    if (!sensor) {
      return res.status(404).json({ error: 'Sensor not found' });
    }
    
    // Construir query para obtener campañas con conversiones de timestamp
    let queryText = `
      SELECT 
        c.*,
        EXTRACT(EPOCH FROM (c.start_date + c.start_time::time))::bigint * 1000 AS start_timestamp_ms,
        EXTRACT(EPOCH FROM (c.end_date + c.end_time::time))::bigint * 1000 AS end_timestamp_ms
      FROM campaigns c
      INNER JOIN campaign_sensors cs ON c.id = cs.campaign_id
      WHERE cs.sensor_mac = $1
    `;
    
    const params: any[] = [mac];
    
    // Añadir filtro de estado si se proporciona, si no, usar estados activos
    if (statusFilter) {
      queryText += ` AND c.status = $2`;
      params.push(statusFilter);
    } else {
      queryText += ` AND c.status IN ('scheduled', 'running')`;
    }
    
    queryText += ` ORDER BY c.start_date ASC`;
    
    // Obtener campañas activas o programadas para este sensor
    const campaignsResult = await query(queryText, params);
    
    // DEBUG: Log raw data from database
    if (campaignsResult.rows.length > 0) {
      console.log(`🔍 DEBUG - Raw campaign data from DB for sensor ${mac}:`);
      campaignsResult.rows.forEach((c: any) => {
        console.log(`  Campaign ID ${c.id}:`);
        console.log(`    start_freq_mhz: ${c.start_freq_mhz} (type: ${typeof c.start_freq_mhz})`);
        console.log(`    end_freq_mhz: ${c.end_freq_mhz} (type: ${typeof c.end_freq_mhz})`);
        console.log(`    start_date: ${c.start_date} (type: ${typeof c.start_date})`);
        console.log(`    start_time: ${c.start_time} (type: ${typeof c.start_time})`);
        console.log(`    end_date: ${c.end_date} (type: ${typeof c.end_date})`);
        console.log(`    end_time: ${c.end_time} (type: ${typeof c.end_time})`);
        console.log(`    config: ${JSON.stringify(c.config)}`);
      });
    }
    
    // Transformar al formato esperado por el sensor (GET-campaigns.jsonc)
    const campaigns = campaignsResult.rows.map((campaign: any) => {
      const config = typeof campaign.config === 'string' ? JSON.parse(campaign.config) : (campaign.config || {});
      
      console.log(`\n📋 Processing campaign ${campaign.id}:`);
      console.log(`  Raw config type: ${typeof campaign.config}`);
      console.log(`  Raw config value:`, campaign.config);
      console.log(`  Parsed config:`, config);
      console.log(`  config.centerFrequency type: ${typeof config.centerFrequency}, value: ${config.centerFrequency}`);
      console.log(`  start_freq_mhz: ${campaign.start_freq_mhz} (type: ${typeof campaign.start_freq_mhz})`);
      console.log(`  end_freq_mhz: ${campaign.end_freq_mhz} (type: ${typeof campaign.end_freq_mhz})`);
      
      // Calcular center_freq_hz - siempre debe tener un valor
      let center_freq_hz = null;
      
      // Opción 1: Calcular desde start_freq_mhz y end_freq_mhz
      if (campaign.start_freq_mhz !== null && campaign.start_freq_mhz !== undefined && 
          campaign.end_freq_mhz !== null && campaign.end_freq_mhz !== undefined) {
        // Convertir a número (PostgreSQL puede devolver NUMERIC como string)
        const startFreq = typeof campaign.start_freq_mhz === 'string' 
          ? parseFloat(campaign.start_freq_mhz) 
          : campaign.start_freq_mhz;
        const endFreq = typeof campaign.end_freq_mhz === 'string' 
          ? parseFloat(campaign.end_freq_mhz) 
          : campaign.end_freq_mhz;
        
        center_freq_hz = Math.round((startFreq + endFreq) / 2 * 1e6);
        console.log(`  ✅ Calculated center_freq_hz: ${center_freq_hz} Hz from start_freq_mhz: ${campaign.start_freq_mhz} (${startFreq}) and end_freq_mhz: ${campaign.end_freq_mhz} (${endFreq})`);
      } 
      // Opción 2: Usar centerFrequency del config (viene en MHz, convertir a Hz)
      else if (config.centerFrequency !== null && config.centerFrequency !== undefined) {
        // Asegurar que sea número (puede venir como string)
        const centerFreqNum = typeof config.centerFrequency === 'string' 
          ? parseFloat(config.centerFrequency) 
          : config.centerFrequency;
        center_freq_hz = Math.round(centerFreqNum * 1e6);
        console.log(`  ✅ Using centerFrequency from config: ${center_freq_hz} Hz (${config.centerFrequency} MHz, parsed as ${centerFreqNum})`);
      }
      // Opción 3: Usar center_freq_hz del config (ya viene en Hz)
      else if (config.center_freq_hz) {
        center_freq_hz = config.center_freq_hz;
        console.log(`  ✅ Using center_freq_hz from config: ${center_freq_hz} Hz`);
      } 
      else {
        console.log(`  ❌ Could not calculate center_freq_hz:`);
        console.log(`     - start_freq_mhz: ${campaign.start_freq_mhz}`);
        console.log(`     - end_freq_mhz: ${campaign.end_freq_mhz}`);
        console.log(`     - config.centerFrequency: ${config.centerFrequency}`);
        console.log(`     - config.center_freq_hz: ${config.center_freq_hz}`);
      }
      
      // Usar timeframe pre-calculado por PostgreSQL
      let timeframe: { start: number | null; end: number | null } = {
        start: campaign.start_timestamp_ms ? parseInt(campaign.start_timestamp_ms) : null,
        end: campaign.end_timestamp_ms ? parseInt(campaign.end_timestamp_ms) : null
      };
      
      console.log(`  Timeframe for campaign ${campaign.id}:`);
      console.log(`    start: ${timeframe.start} (${timeframe.start ? new Date(timeframe.start).toISOString() : 'null'})`);
      console.log(`    end: ${timeframe.end} (${timeframe.end ? new Date(timeframe.end).toISOString() : 'null'})`)
      
      return {
        campaign_id: campaign.id,
        status: campaign.status,
        center_freq_hz: center_freq_hz,
        rbw_hz: campaign.resolution_khz ? campaign.resolution_khz * 1000 : 10000,
        sample_rate_hz: config.sample_rate_hz || 20000000,
        antenna_port: config.antenna_port || 1,
        acquisition_period_s: campaign.interval_seconds || 300,
        window: config.window || 'hamming',
        overlap: config.overlap || 0.5,
        lna_gain: config.lna_gain || 0,
        vga_gain: config.vga_gain || 0,
        antenna_amp: config.antenna_amp !== undefined ? config.antenna_amp : false,
        timeframe: timeframe,
        // Filter: Prioridad 1: config.filter, Prioridad 2: start/end freq de campaña
        filter: config.filter ? config.filter : (
          campaign.start_freq_mhz && campaign.end_freq_mhz ? {
            start_freq_hz: Math.round(parseFloat(campaign.start_freq_mhz) * 1e6),
            end_freq_hz: Math.round(parseFloat(campaign.end_freq_mhz) * 1e6)
          } : null
        )
      };
    });
    console.log(`📋 Campaigns for sensor ${mac}:`, campaigns.length);
    
    res.json({ campaigns });
  } catch (error: any) {
    console.error('Error getting campaigns:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensor/{mac}/realtime:
 *   get:
 *     summary: Obtener configuración de tiempo real para el sensor
 *     description: |
 *       Endpoint para que los sensores obtengan su configuración de adquisición en tiempo real.
 *       Estructura compatible con GET-realtime.jsonc del sensor (NUEVO FORMATO).
 *       
 *       **Cambios en el nuevo formato:**
 *       - ❌ Campo `span` eliminado (redundante con `sample_rate_hz`)
 *       - ❌ Campo `scale` eliminado
 *       - ✅ `demodulation` ahora es un string simple ("am", "fm") o null (antes era objeto)
 *       - ✅ `filter` ahora usa `{start_freq_hz, end_freq_hz}` (antes usaba `{type, bw_hz, order}`)
 *     tags: [Sensor Query]
 *     parameters:
 *       - in: path
 *         name: mac
 *         required: true
 *         schema:
 *           type: string
 *         description: Dirección MAC del sensor
 *         example: "00:11:22:33:44:55"
 *     responses:
 *       200:
 *         description: Configuración de tiempo real (NUEVO FORMATO)
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 center_freq_hz:
 *                   type: number
 *                   description: Frecuencia central en Hz
 *                   example: 97500000
 *                 rbw_hz:
 *                   type: number
 *                   description: Resolution Bandwidth en Hz
 *                   example: 100000
 *                 sample_rate_hz:
 *                   type: number
 *                   description: Tasa de muestreo en Hz (reemplaza span)
 *                   example: 20000000
 *                 window:
 *                   type: string
 *                   description: Tipo de ventana
 *                   example: "hamming"
 *                 overlap:
 *                   type: number
 *                   description: Overlap factor (0-1)
 *                   example: 0.5
 *                 lna_gain:
 *                   type: number
 *                   description: Ganancia LNA en dB
 *                   example: 0
 *                 vga_gain:
 *                   type: number
 *                   description: Ganancia VGA en dB
 *                   example: 0
 *                 antenna_amp:
 *                   type: boolean
 *                   description: Amplificador de antena activado
 *                   example: true
 *                 antenna_port:
 *                   type: number
 *                   description: Puerto de antena (1-4)
 *                   example: 1
 *                 demodulation:
 *                   type: string
 *                   nullable: true
 *                   description: Tipo de demodulación ("am", "fm") o null (NUEVO FORMATO simplificado)
 *                   example: "fm"
 *                 filter:
 *                   type: object
 *                   nullable: true
 *                   description: Filtro de frecuencias (NUEVO FORMATO con rangos)
 *                   properties:
 *                     start_freq_hz:
 *                       type: number
 *                       example: 87500000
 *                     end_freq_hz:
 *                       type: number
 *                       example: 107500000
 *             example:
 *               center_freq_hz: 97500000
 *               rbw_hz: 100000
 *               sample_rate_hz: 20000000
 *               window: "hamming"
 *               overlap: 0.5
 *               lna_gain: 0
 *               vga_gain: 0
 *               antenna_amp: true
 *               antenna_port: 1
 *               demodulation: "fm"
 *               filter:
 *                 start_freq_hz: 87500000
 *                 end_freq_hz: 107500000
 *       404:
 *         description: Sensor no encontrado
 */
router.get('/:mac/realtime', async (req: Request, res: Response) => {
  try {
    const mac = req.params.mac;
    
    // Obtener configuración activa para este sensor
    const configResult = await query(`
      SELECT * FROM sensor_configurations 
      WHERE mac = $1 AND is_active = 1 
      ORDER BY created_at DESC 
      LIMIT 1
    `, [mac]);
    
    if (configResult.rows.length === 0) {
      // Si no hay configuración, devolver configuración de STOP (center_freq = 0)
      // Esto indica al sensor que debe estar en modo inactivo
      return res.json({
        center_freq_hz: 0,
        rbw_hz: 0,
        sample_rate_hz: 0,
        window: 'none',
        overlap: 0,
        lna_gain: 0,
        vga_gain: 0,
        antenna_amp: false,
        antenna_port: 0,
        demodulation: null,
        filter: null
      });
    }
    
    const config = configResult.rows[0];
    
    // Calcular center_frequency y span desde start_freq_hz y end_freq_hz
    const centerFreqHz = Math.round((Number(config.start_freq_hz) + Number(config.end_freq_hz)) / 2);
    const spanHz = Number(config.end_freq_hz) - Number(config.start_freq_hz);
    
    // Si center_freq_hz es 0, es una señal de STOP
    if (centerFreqHz === 0) {
      console.log(`🛑 GET /realtime para sensor ${mac}: STOP (center_freq_hz = 0)`);
      return res.json({
        center_freq_hz: 0,
        rbw_hz: 0,
        sample_rate_hz: 0,
        window: 'none',
        overlap: 0,
        lna_gain: 0,
        vga_gain: 0,
        antenna_amp: false,
        antenna_port: 0,
        demodulation: null,
        filter: null
      });
    }
    
    console.log(`📡 GET /realtime para sensor ${mac}:`, {
      start_freq_hz: config.start_freq_hz,
      end_freq_hz: config.end_freq_hz,
      center_freq_hz: centerFreqHz,
      span: spanHz,
      antenna_port: config.antenna_port
    });
    
    // Transformar al formato esperado por el sensor (GET-realtime.jsonc - NUEVO FORMATO)
    const realtimeConfig = {
      center_freq_hz: centerFreqHz,
      rbw_hz: Number(config.resolution_hz) || 10000,
      sample_rate_hz: Number(config.sample_rate_hz) || 20000000,
      window: config.window || 'hamming',
      overlap: Number(config.overlap) || 0.5,
      lna_gain: Number(config.lna_gain) || 0,
      vga_gain: Number(config.vga_gain) || 0,
      antenna_amp: Boolean(config.antenna_amp),
      antenna_port: Number(config.antenna_port) || 1,
      // Demodulation: ahora es un string simple ("am", "fm") o null
      demodulation: config.demod_type ? config.demod_type.toLowerCase() : null,
      // Filter: ahora usa start_freq_hz y end_freq_hz en lugar de tipo de filtro
      filter: (config.filter_start_freq_hz && config.filter_end_freq_hz) ? {
        start_freq_hz: Number(config.filter_start_freq_hz),
        end_freq_hz: Number(config.filter_end_freq_hz)
      } : (config.filter_type ? {
        // Soporte retrocompatibilidad para filtros antiguos
        type: config.filter_type,
        bw_hz: Number(config.filter_bw_hz),
        order: Number(config.filter_order)
      } : null)
    };
    
    res.json(realtimeConfig);
  } catch (error: any) {
    console.error('Error getting realtime config:', error);
    res.status(500).json({ error: error.message });
  }
});

export default router;
