import { query } from '../database/connection';
import { Sensor } from '../types';
import { SensorHistoryAlertModel } from './SensorHistoryAlert';

export class SensorModel {
  // Helper para normalizar datos numéricos de PostgreSQL
  private static normalizeSensor(row: any): Sensor {
    return {
      ...row,
      lat: row.lat ? parseFloat(row.lat) : undefined,
      lng: row.lng ? parseFloat(row.lng) : undefined,
      alt: row.alt ? parseFloat(row.alt) : undefined,
      id: row.id ? parseInt(row.id) : undefined,
      created_at: row.created_at ? parseInt(row.created_at) : undefined,
      updated_at: row.updated_at ? parseInt(row.updated_at) : undefined,
      status_admin: row.status_admin || 'active',
    };
  }

  private static isValidStatus(status: string): boolean {
    return ['active', 'inactive', 'online', 'offline', 'busy', 'error', 'delay'].includes(status);
  }

  static async getAll(): Promise<Sensor[]> {
    const result = await query('SELECT * FROM sensors ORDER BY created_at DESC');
    return result.rows.map(row => this.normalizeSensor(row));
  }

  static async getById(id: number): Promise<Sensor | undefined> {
    const result = await query('SELECT * FROM sensors WHERE id = $1', [id]);
    return result.rows[0] ? this.normalizeSensor(result.rows[0]) : undefined;
  }

  static async getByMac(mac: string): Promise<Sensor | undefined> {
    const result = await query('SELECT * FROM sensors WHERE mac = $1', [mac]);
    return result.rows[0] ? this.normalizeSensor(result.rows[0]) : undefined;
  }

  static async create(sensor: Sensor, userId?: number): Promise<Sensor> {
    const result = await query(
      `INSERT INTO sensors (mac, name, description, lat, lng, alt, status, status_admin, created_by)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
       RETURNING id`,
      [
        sensor.mac,
        sensor.name,
        sensor.description || null,
        sensor.lat || null,
        sensor.lng || null,
        sensor.alt || null,
        sensor.status || 'offline',
        sensor.status_admin || 'active',
        userId || null
      ]
    );
    
    return (await this.getById(result.rows[0].id))!;
  }

  static async update(id: number, sensor: Partial<Sensor>, userId?: number): Promise<Sensor | undefined> {
    const updates: string[] = [];
    const values: any[] = [];
    let paramIndex = 1;

    if (sensor.name !== undefined) {
      updates.push(`name = $${paramIndex++}`);
      values.push(sensor.name);
    }
    if (sensor.description !== undefined) {
      updates.push(`description = $${paramIndex++}`);
      values.push(sensor.description);
    }
    if (sensor.lat !== undefined) {
      updates.push(`lat = $${paramIndex++}`);
      values.push(sensor.lat);
    }
    if (sensor.lng !== undefined) {
      updates.push(`lng = $${paramIndex++}`);
      values.push(sensor.lng);
    }
    if (sensor.alt !== undefined) {
      updates.push(`alt = $${paramIndex++}`);
      values.push(sensor.alt);
    }
    if (sensor.status !== undefined) {
      updates.push(`status = $${paramIndex++}`);
      values.push(sensor.status);
    }
    if (sensor.status_admin !== undefined) {
      updates.push(`status_admin = $${paramIndex++}`);
      values.push(sensor.status_admin);
    }

    if (updates.length === 0) {
      return this.getById(id);
    }

    updates.push(`updated_at = $${paramIndex++}`);
    values.push(Date.now());
    
    if (userId !== undefined) {
      updates.push(`updated_by = $${paramIndex++}`);
      values.push(userId);
    }
    
    values.push(id);

    await query(
      `UPDATE sensors SET ${updates.join(', ')} WHERE id = $${paramIndex}`,
      values
    );
    
    return this.getById(id);
  }

  static async delete(id: number): Promise<boolean> {
    const result = await query('DELETE FROM sensors WHERE id = $1', [id]);
    return (result.rowCount || 0) > 0;
  }

  static async updateLocation(mac: string, lat: number, lng: number, alt?: number): Promise<void> {
    await query(
      `UPDATE sensors SET lat = $1, lng = $2, alt = $3, updated_at = $4 WHERE mac = $5`,
      [lat, lng, alt || null, Date.now(), mac]
    );
  }

  static async updateStatus(mac: string, status: string): Promise<void> {
    if (!this.isValidStatus(status)) {
      throw new Error(`Invalid status: ${status}. Must be 'active', 'inactive', 'online', 'offline', 'busy', 'error', or 'delay'.`);
    }

    await query(
      `UPDATE sensors SET status = $1, updated_at = $2 WHERE mac = $3`,
      [status, Date.now(), mac]
    );
  }

  static async validateAndUpdateStatus(): Promise<any> {
    // Obtener todos los sensores
    const sensorsResult = await query('SELECT * FROM sensors');
    const sensors = sensorsResult.rows;
    
    const updatedSensors: any[] = [];
    // Umbral de 30 segundos → estado 'delay' (en espera)
    const thirtySecondsAgo = Date.now() - (30 * 1000);
    // Umbral de 1 minuto → estado 'offline'
    const oneMinuteAgo = Date.now() - (60 * 1000);
    
    for (const sensor of sensors) {
      // Ignorar si el sensor está administrativamente inactivo
      if (sensor.status_admin === 'inactive') continue;

      // Si el sensor está ocupado (busy), no cambiamos su estado automáticamente
      // asumiendo que está en una tarea de larga duración.
      if (sensor.status === 'busy') continue;

      // Obtener el último status del sensor
      // Usamos created_at (tiempo del servidor) en lugar de timestamp_ms (tiempo del sensor)
      // para evitar problemas de sincronización de relojes o zonas horarias.
      const statusResult = await query(
        `SELECT EXTRACT(EPOCH FROM created_at) * 1000 as server_timestamp_ms 
         FROM sensor_status 
         WHERE mac = $1 
         ORDER BY created_at DESC 
         LIMIT 1`,
        [sensor.mac]
      );
      
      let shouldBeOffline = false;
      let shouldBeDelay = false;
      let lastUpdate = null;
      
      if (statusResult.rows.length === 0) {
        // Sin información de status → offline directamente
        shouldBeOffline = true;
      } else {
        lastUpdate = parseFloat(statusResult.rows[0].server_timestamp_ms);
        if (lastUpdate <= oneMinuteAgo) {
          // Sin status por más de 1 minuto → offline
          shouldBeOffline = true;
        } else if (lastUpdate <= thirtySecondsAgo) {
          // Sin status entre 30 segundos y 1 minuto → delay (en espera)
          shouldBeDelay = true;
        }
      }
      
      // online/active → delay (entre 30s y 60s sin status)
      if (shouldBeDelay && (sensor.status === 'online' || sensor.status === 'active')) {
        await this.updateStatus(sensor.mac, 'delay');
        updatedSensors.push({
          mac: sensor.mac,
          name: sensor.name,
          previousStatus: sensor.status,
          newStatus: 'delay',
          lastUpdate: lastUpdate,
          secondsSinceUpdate: lastUpdate ? ((Date.now() - lastUpdate) / 1000).toFixed(0) : null
        });
      }
      // online/active/delay → offline (más de 1 minuto sin status)
      else if (shouldBeOffline && (sensor.status === 'online' || sensor.status === 'active' || sensor.status === 'delay')) {
        await this.updateStatus(sensor.mac, 'offline');
        
        // Crear alerta de desconexión solo si venía de un estado activo
        await SensorHistoryAlertModel.create({
          sensor_mac: sensor.mac,
          alert_type: 'Offline',
          description: `Sensor desconectado. Última actualización: ${lastUpdate ? new Date(lastUpdate).toLocaleString() : 'Nunca'}`,
          timestamp: Date.now()
        });

        updatedSensors.push({
          mac: sensor.mac,
          name: sensor.name,
          previousStatus: sensor.status,
          newStatus: 'offline',
          lastUpdate: lastUpdate,
          minutesSinceUpdate: lastUpdate ? ((Date.now() - lastUpdate) / (1000 * 60)).toFixed(1) : null
        });
      }
      // delay/offline → online (recibió status reciente)
      else if (!shouldBeOffline && !shouldBeDelay && (sensor.status === 'offline' || sensor.status === 'delay')) {
        await this.updateStatus(sensor.mac, 'online');
        updatedSensors.push({
          mac: sensor.mac,
          name: sensor.name,
          previousStatus: sensor.status,
          newStatus: 'online',
          lastUpdate: lastUpdate,
          secondsSinceUpdate: lastUpdate ? ((Date.now() - lastUpdate) / 1000).toFixed(0) : null
        });
      }
      // Migración de estados antiguos (active/inactive) a nuevos (online/offline/delay)
      else if (sensor.status === 'active' || sensor.status === 'inactive') {
        const newStatus = shouldBeOffline ? 'offline' : (shouldBeDelay ? 'delay' : 'online');
        if (sensor.status !== newStatus) {
           await this.updateStatus(sensor.mac, newStatus);
           updatedSensors.push({
            mac: sensor.mac,
            name: sensor.name,
            previousStatus: sensor.status,
            newStatus: newStatus,
            lastUpdate: lastUpdate,
            minutesSinceUpdate: lastUpdate ? ((Date.now() - lastUpdate) / (1000 * 60)).toFixed(1) : null
          });
        }
      }
    }
    
    return {
      updated: updatedSensors.length,
      sensors: updatedSensors,
      checkedAt: new Date().toISOString()
    };
  }
}
