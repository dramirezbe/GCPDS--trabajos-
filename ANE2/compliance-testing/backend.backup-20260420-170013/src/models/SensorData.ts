import { query, getClient } from '../database/connection';
import { SensorStatus, SensorGPS, SensorData, SensorConfiguration } from '../types';
import { SensorHistoryAlertModel } from './SensorHistoryAlert';

export class SensorDataModel {
  // Cache en memoria para datos en tiempo real (Monitoreo)
  // Map<mac, data[]>
  private static latestDataCache: Map<string, any[]> = new Map();

  // Método para actualizar el cache en memoria (se llama siempre, guarde o no en DB)
  static updateCache(data: SensorData): void {
    const currentCache = this.latestDataCache.get(data.mac) || [];
    
    // Preparar el objeto de datos
    const cachedItem = {
      ...data,
      // Asegurar que Pxx sea un array (ya debería serlo)
      Pxx: Array.isArray(data.Pxx) ? data.Pxx : JSON.parse(data.Pxx as any),
      // Asegurar timestamp
      timestamp: data.timestamp || Date.now()
    };
    
    // Agregar al inicio
    const newCache = [cachedItem, ...currentCache].slice(0, 100); // Mantener últimos 100 en memoria
    this.latestDataCache.set(data.mac, newCache);
  }

  // Status
  static async saveStatus(status: SensorStatus): Promise<void> {
    await query(
      `INSERT INTO sensor_status (
        mac, cpu_0, cpu_1, cpu_2, cpu_3, ram_mb, swap_mb, disk_mb, temp_c,
        total_ram_mb, total_swap_mb, total_disk_mb, delta_t_ms, ping_ms,
        timestamp_ms, last_kal_ms, last_ntp_ms, logs
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)`,
      [
        status.mac,
        status.metrics.cpu[0] || null,
        status.metrics.cpu[1] || null,
        status.metrics.cpu[2] || null,
        status.metrics.cpu[3] || null,
        status.metrics.ram_mb,
        status.metrics.swap_mb,
        status.metrics.disk_mb,
        status.metrics.temp_c,
        status.total_metrics.ram_mb,
        status.total_metrics.swap_mb,
        status.total_metrics.disk_mb,
        status.delta_t_ms,
        status.ping_ms,
        status.timestamp_ms,
        status.last_kal_ms,
        status.last_ntp_ms,
        status.logs
      ]
    );

    // Generar Alertas Históricas
    try {
      const timestamp = status.timestamp_ms || Date.now();
      
      // 1. CPU — usar el máximo de núcleos con carga >0 (coincide con umbral rojo de tarjeta)
      const cpu = (status.metrics.cpu || []).map((c: any) => Number(c)).filter((c: number) => c > 0);
      const maxCpu = cpu.length > 0 ? Math.max(...cpu) : 0;
      if (maxCpu > 80) {
        if (await SensorHistoryAlertModel.shouldCreateAlert(status.mac, 'CPU Alta')) {
          await SensorHistoryAlertModel.create({
            sensor_mac: status.mac,
            alert_type: 'CPU Alta',
            description: `CPU máxima: ${maxCpu.toFixed(1)}%`,
            timestamp: timestamp
          });
        }
      }

      // 2. RAM
      if (status.total_metrics.ram_mb > 0) {
        const ramUsage = (Number(status.metrics.ram_mb) / Number(status.total_metrics.ram_mb)) * 100;
        if (ramUsage > 80) {
          if (await SensorHistoryAlertModel.shouldCreateAlert(status.mac, 'RAM Crítica')) {
            await SensorHistoryAlertModel.create({
              sensor_mac: status.mac,
              alert_type: 'RAM Crítica',
              description: `Uso de RAM: ${ramUsage.toFixed(1)}%`,
              timestamp: timestamp
            });
          }
        }
      }

      // 3. Disco
      if (status.total_metrics.disk_mb > 0) {
        const diskUsage = (Number(status.metrics.disk_mb) / Number(status.total_metrics.disk_mb)) * 100;
        if (diskUsage > 85) {
          if (await SensorHistoryAlertModel.shouldCreateAlert(status.mac, 'Disco Crítico')) {
            await SensorHistoryAlertModel.create({
              sensor_mac: status.mac,
              alert_type: 'Disco Crítico',
              description: `Uso de Disco: ${diskUsage.toFixed(1)}%`,
              timestamp: timestamp
            });
          }
        }
      }

      // 4. Temperatura (ignorar valores 0 o negativos que son claramente inválidos)
      // Umbral: >70°C (igual al umbral rojo de la tarjeta de estado del sensor)
      if (status.metrics.temp_c && Number(status.metrics.temp_c) > 0 && Number(status.metrics.temp_c) > 70) {
        const tempAlert = Number(status.metrics.temp_c) > 85 ? 'Temperatura Crítica' : 'Temperatura Alta';
        console.log(`🌡️ ALERTA: Sensor ${status.mac} - ${tempAlert}: ${Number(status.metrics.temp_c).toFixed(1)}°C`);
        if (await SensorHistoryAlertModel.shouldCreateAlert(status.mac, tempAlert)) {
          await SensorHistoryAlertModel.create({
            sensor_mac: status.mac,
            alert_type: tempAlert,
            description: `Temperatura: ${Number(status.metrics.temp_c).toFixed(1)}°C`,
            timestamp: timestamp
          });
          console.log(`✅ Alerta de temperatura guardada en historial para sensor ${status.mac}`);
        }
      }

      // 4b. Swap
      if (status.total_metrics.swap_mb > 0) {
        const swapUsage = (Number(status.metrics.swap_mb) / Number(status.total_metrics.swap_mb)) * 100;
        if (swapUsage > 80) {
          if (await SensorHistoryAlertModel.shouldCreateAlert(status.mac, 'Swap Crítico')) {
            await SensorHistoryAlertModel.create({
              sensor_mac: status.mac,
              alert_type: 'Swap Crítico',
              description: `Uso de Swap: ${swapUsage.toFixed(1)}%`,
              timestamp: timestamp
            });
          }
        }
      }

      // 5. Latencia Alta
      if (status.ping_ms && Number(status.ping_ms) > 250) {
        if (await SensorHistoryAlertModel.shouldCreateAlert(status.mac, 'Latencia Alta', 15)) {
          await SensorHistoryAlertModel.create({
            sensor_mac: status.mac,
            alert_type: 'Latencia Alta',
            description: `Latencia: ${Number(status.ping_ms).toFixed(0)}ms`,
            timestamp: timestamp
          });
        }
      }

      // 6. Logs Error
      if (status.logs && status.logs.includes('ERROR')) {
        if (await SensorHistoryAlertModel.shouldCreateAlert(status.mac, 'Error en Logs', 60)) {
          const errorLine = status.logs.split('\n').find((l: string) => l.includes('ERROR')) || 'Error detectado en logs';
          await SensorHistoryAlertModel.create({
            sensor_mac: status.mac,
            alert_type: 'Error en Logs',
            description: errorLine.substring(0, 250),
            timestamp: timestamp
          });
        }
      }

      // 7. Logs Warning (menos frecuente, 2 horas)
      if (status.logs && status.logs.includes('WARN')) {
        if (await SensorHistoryAlertModel.shouldCreateAlert(status.mac, 'Advertencia en Logs', 120)) {
          const warnLine = status.logs.split('\n').find((l: string) => l.includes('WARN')) || 'Advertencia detectada en logs';
          await SensorHistoryAlertModel.create({
            sensor_mac: status.mac,
            alert_type: 'Advertencia en Logs',
            description: warnLine.substring(0, 250),
            timestamp: timestamp
          });
        }
      }
    } catch (e) {
      console.error('Error saving alert history:', e);
    }
  }

  static async getLatestStatus(mac: string): Promise<any> {
    // Buscar el último estado que tenga métricas válidas (evitar heartbeats vacíos)
    // Y que NO esté en el futuro (tolerancia de 5 minutos = 300000 ms) para evitar timestamps incorrectos
    // IMPORTANTE: Usar Date.now() en lugar de la hora de la DB para ser estricto con el tiempo del servidor de aplicación
    const serverTime = Date.now() + 300000;
    
    // NO filtramos por cpu_0 IS NOT NULL porque un núcleo con 0% se guarda como NULL
    // y haría que se omitiera el registro más reciente (retornando datos obsoletos o null).
    // La validación del endpoint garantiza que todos los registros tienen métricas de CPU.
    const result = await query(
      `SELECT * FROM sensor_status 
       WHERE mac = $1 
       AND timestamp_ms <= $2
       ORDER BY timestamp_ms DESC LIMIT 1`,
      [mac, serverTime]
    );
    
    const row = result.rows[0];
    if (!row) return null;
    
    // Log de diagnóstico para temperatura
    if (row.temp_c) {
      console.log(`🌡️ Status para ${mac} - Temperatura: ${row.temp_c}°C`);
    }
    
    // Transformar los datos de la BD al formato que espera el frontend
    return {
      mac: row.mac,
      metrics: {
        cpu: [
          row.cpu_0 || 0,
          row.cpu_1 || 0,
          row.cpu_2 || 0,
          row.cpu_3 || 0
        ],
        ram_mb: row.ram_mb || 0,
        swap_mb: row.swap_mb || 0,
        disk_mb: row.disk_mb || 0,
        temp_c: row.temp_c || 0
      },
      total_metrics: {
        ram_mb: row.total_ram_mb || 0,
        swap_mb: row.total_swap_mb || 0,
        disk_mb: row.total_disk_mb || 0
      },
      delta_t_ms: row.delta_t_ms || 0,
      ping_ms: row.ping_ms || 0,
      timestamp_ms: row.timestamp_ms,
      last_kal_ms: row.last_kal_ms || 0,
      last_ntp_ms: row.last_ntp_ms || 0,
      logs: row.logs || ''
    };
  }

  // GPS
  static async saveGPS(gps: SensorGPS): Promise<void> {
    await query(
      `INSERT INTO sensor_gps (mac, lat, lng, alt) VALUES ($1, $2, $3, $4)`,
      [gps.mac, gps.lat, gps.lng, gps.alt || null]
    );
  }

  static async getLatestGPS(mac: string): Promise<any> {
    const result = await query(
      `SELECT * FROM sensor_gps WHERE mac = $1 ORDER BY created_at DESC LIMIT 1`,
      [mac]
    );
    return result.rows[0];
  }

  // Data (spectrum)
  static async saveData(data: SensorData): Promise<void> {
    await query(
      `INSERT INTO sensor_data (
        mac, campaign_id, pxx, start_freq_hz, end_freq_hz, timestamp, lat, lng,
        excursion_peak_to_peak_hz, excursion_peak_deviation_hz, excursion_rms_deviation_hz,
        depth_peak_to_peak, depth_peak_deviation, depth_rms_deviation, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)`,
      [
        data.mac,
        data.campaign_id || null,
        JSON.stringify(data.Pxx),
        data.start_freq_hz,
        data.end_freq_hz,
        data.timestamp,
        data.lat || null,
        data.lng || null,
        data.excursion?.peak_to_peak_hz || null,
        data.excursion?.peak_deviation_hz || null,
        data.excursion?.rms_deviation_hz || null,
        data.depth?.peak_to_peak || null,
        data.depth?.peak_deviation || null,
        data.depth?.rms_deviation || null,
        Date.now() // created_at timestamp
      ]
    );
  }

  static async getLatestData(mac: string, limit: number = 100): Promise<any[]> {
    // 1. Intentar obtener del cache primero (más rápido y contiene datos de "Monitoreo" no guardados)
    const cachedData = this.latestDataCache.get(mac);
    
    if (cachedData && cachedData.length > 0) {
      // Devolver los últimos 'limit' registros del cache
      // Verificar si el cache tiene datos recientes (ej. últimos 5 segundos)
      // Si el cache es muy viejo, quizás deberíamos consultar la DB por si acaso, 
      // pero para "latest data" el cache es la verdad absoluta de lo que acaba de llegar.
      return cachedData.slice(0, limit);
    }

    // 2. Si no hay cache, consultar DB (datos persistidos)
    const result = await query(
      `SELECT * FROM sensor_data WHERE mac = $1 ORDER BY timestamp DESC LIMIT $2`,
      [mac, limit]
    );
    return result.rows.map((row: any) => ({
      ...row,
      Pxx: JSON.parse(row.pxx),
      lat: row.lat ? parseFloat(row.lat) : undefined,
      lng: row.lng ? parseFloat(row.lng) : undefined,
      start_freq_hz: row.start_freq_hz ? parseInt(row.start_freq_hz) : undefined,
      end_freq_hz: row.end_freq_hz ? parseInt(row.end_freq_hz) : undefined,
      timestamp: row.timestamp ? parseInt(row.timestamp) : undefined,
    }));
  }

  static async getDataByTimeRange(mac: string, startTime: number, endTime: number): Promise<any[]> {
    const result = await query(
      `SELECT * FROM sensor_data 
       WHERE mac = $1 AND timestamp >= $2 AND timestamp <= $3
       ORDER BY timestamp ASC`,
      [mac, startTime, endTime]
    );
    return result.rows.map((row: any) => ({
      ...row,
      Pxx: JSON.parse(row.pxx),
      lat: row.lat ? parseFloat(row.lat) : undefined,
      lng: row.lng ? parseFloat(row.lng) : undefined,
      start_freq_hz: row.start_freq_hz ? parseInt(row.start_freq_hz) : undefined,
      end_freq_hz: row.end_freq_hz ? parseInt(row.end_freq_hz) : undefined,
      timestamp: row.timestamp ? parseInt(row.timestamp) : undefined,
    }));
  }

  // Configuration
  static async saveConfiguration(config: SensorConfiguration): Promise<any> {
    // Calcular start_freq y end_freq para el rango del scan
    let startFreq, endFreq;
    
    // PRIORIDAD 1: Usar center_frequency y sample_rate_hz (frecuencia central real del scan)
    // Se usa !== undefined para permitir valor 0 (usado para detener adquisición)
    if (config.center_frequency !== undefined && config.sample_rate_hz !== undefined) {
      startFreq = config.center_frequency - (config.sample_rate_hz / 2);
      endFreq = config.center_frequency + (config.sample_rate_hz / 2);
    }
    // PRIORIDAD 2: Formato antiguo con span (retrocompatibilidad)
    else if (config.center_frequency !== undefined && config.span !== undefined) {
      startFreq = config.center_frequency - (config.span / 2);
      endFreq = config.center_frequency + (config.span / 2);
    }
    // PRIORIDAD 3: Si vienen start_freq_hz y end_freq_hz directamente (solo si no hay center_frequency)
    // NOTA: start_freq_hz/end_freq_hz pueden ser del FILTRO, no del scan completo
    else if (config.start_freq_hz !== undefined && config.end_freq_hz !== undefined) {
      startFreq = config.start_freq_hz;
      endFreq = config.end_freq_hz;
    } 
    else {
      throw new Error('Configuration must include center_frequency with sample_rate_hz or span, or start_freq_hz/end_freq_hz');
    }

    // Desactivar configuraciones anteriores
    await query(
      `UPDATE sensor_configurations SET is_active = 0 WHERE mac = $1`,
      [config.mac]
    );

    const result = await query(
      `INSERT INTO sensor_configurations (
        mac, start_freq_hz, end_freq_hz, resolution_hz, antenna_port, "window", overlap,
        sample_rate_hz, lna_gain, vga_gain, antenna_amp, demod_type, demod_bandwidth_hz,
        demod_center_freq_hz, demod_with_metrics, demod_port_socket, filter_type, filter_bw_hz,
        filter_order, filter_start_freq_hz, filter_end_freq_hz, is_active, is_monitoring
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, 1, $22)
      RETURNING id`,
      [
        config.mac,
        startFreq,
        endFreq,
        config.resolution_hz || null,
        config.antenna_port || null,
        config.window || null,
        config.overlap || null,
        config.sample_rate_hz || null,
        config.lna_gain || null,
        config.vga_gain || null,
        config.antenna_amp ? 1 : 0,
        config.demod_type || config.demodulation?.type || null,
        config.demodulation?.bandwidth_hz || null,
        config.demodulation?.center_freq_hz || null,
        config.demodulation?.with_metrics ? 1 : 0,
        config.demodulation?.port_socket || null,
        config.filter?.type || null,
        config.filter?.bw_hz || null,
        config.filter?.order || null,
        config.filter_start_freq_hz || config.filter?.start_freq_hz || null,
        config.filter_end_freq_hz || config.filter?.end_freq_hz || null,
        config.is_monitoring ? 1 : 0
      ]
    );

    return { id: result.rows[0].id };
  }

  static async getActiveConfiguration(mac: string): Promise<any> {
    const result = await query(
      `SELECT * FROM sensor_configurations WHERE mac = $1 AND is_active = 1 ORDER BY created_at DESC LIMIT 1`,
      [mac]
    );
    
    const config = result.rows[0];
    if (!config) return null;

    // Calcular center_frequency y span desde start_freq y end_freq almacenados
    const centerFrequency = (Number(config.start_freq_hz) + Number(config.end_freq_hz)) / 2;
    const span = Number(config.end_freq_hz) - Number(config.start_freq_hz);

    // Reconstruir objeto con center_frequency y span
    return {
      id: config.id,
      mac: config.mac,
      center_frequency: centerFrequency,
      span: span,
      resolution_hz: config.resolution_hz,
      antenna_port: config.antenna_port,
      window: config.window,
      overlap: config.overlap,
      sample_rate_hz: config.sample_rate_hz,
      lna_gain: config.lna_gain,
      vga_gain: config.vga_gain,
      antenna_amp: config.antenna_amp === 1,
      demodulation: config.demod_type ? {
        type: config.demod_type,
        bandwidth_hz: config.demod_bandwidth_hz,
        center_freq_hz: config.demod_center_freq_hz,
        with_metrics: config.demod_with_metrics === 1,
        port_socket: config.demod_port_socket
      } : undefined,
      filter: (config.filter_start_freq_hz && config.filter_end_freq_hz) ? {
        start_freq_hz: Number(config.filter_start_freq_hz),
        end_freq_hz: Number(config.filter_end_freq_hz)
      } : (config.filter_type ? {
        type: config.filter_type,
        bw_hz: config.filter_bw_hz,
        order: config.filter_order
      } : undefined),
      is_monitoring: config.is_monitoring === 1,
      created_at: config.created_at,
      updated_at: config.updated_at
    };
  }
}
