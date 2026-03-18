import { query } from '../database/connection';
import { Antenna } from '../types';

export class AntennaModel {
  // Helper para normalizar datos numéricos de PostgreSQL
  private static normalizeAntenna(row: any): Antenna {
    return {
      ...row,
      id: row.id ? parseInt(row.id) : undefined,
      frequency_min_hz: row.frequency_min_hz ? parseInt(row.frequency_min_hz) : undefined,
      frequency_max_hz: row.frequency_max_hz ? parseInt(row.frequency_max_hz) : undefined,
      gain_db: row.gain_db ? parseFloat(row.gain_db) : undefined,
      inventory_code: row.inventory_code,
      created_at: row.created_at ? parseInt(row.created_at) : undefined,
      updated_at: row.updated_at ? parseInt(row.updated_at) : undefined,
    };
  }

  static async getAll(): Promise<Antenna[]> {
    const result = await query('SELECT * FROM antennas ORDER BY created_at DESC');
    return result.rows.map(row => this.normalizeAntenna(row));
  }

  static async getById(id: number): Promise<Antenna | undefined> {
    const result = await query('SELECT * FROM antennas WHERE id = $1', [id]);
    return result.rows[0] ? this.normalizeAntenna(result.rows[0]) : undefined;
  }

  static async create(antenna: Antenna, userId?: number): Promise<Antenna> {
    const result = await query(
      `INSERT INTO antennas (name, type, frequency_min_hz, frequency_max_hz, gain_db, description, inventory_code, created_by)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
       RETURNING id`,
      [
        antenna.name,
        antenna.type,
        antenna.frequency_min_hz || null,
        antenna.frequency_max_hz || null,
        antenna.gain_db || null,
        antenna.description || null,
        antenna.inventory_code || null,
        userId || null
      ]
    );
    
    return (await this.getById(result.rows[0].id))!;
  }

  static async update(id: number, antenna: Partial<Antenna>, userId?: number): Promise<Antenna | undefined> {
    const updates: string[] = [];
    const values: any[] = [];
    let paramIndex = 1;

    if (antenna.name !== undefined) {
      updates.push(`name = $${paramIndex++}`);
      values.push(antenna.name);
    }
    if (antenna.type !== undefined) {
      updates.push(`type = $${paramIndex++}`);
      values.push(antenna.type);
    }
    if (antenna.frequency_min_hz !== undefined) {
      updates.push(`frequency_min_hz = $${paramIndex++}`);
      values.push(antenna.frequency_min_hz);
    }
    if (antenna.frequency_max_hz !== undefined) {
      updates.push(`frequency_max_hz = $${paramIndex++}`);
      values.push(antenna.frequency_max_hz);
    }
    if (antenna.gain_db !== undefined) {
      updates.push(`gain_db = $${paramIndex++}`);
      values.push(antenna.gain_db);
    }
    if (antenna.description !== undefined) {
      updates.push(`description = $${paramIndex++}`);
      values.push(antenna.description);
    }
    if (antenna.inventory_code !== undefined) {
      updates.push(`inventory_code = $${paramIndex++}`);
      values.push(antenna.inventory_code);
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
      `UPDATE antennas SET ${updates.join(', ')} WHERE id = $${paramIndex}`,
      values
    );
    
    return this.getById(id);
  }

  static async delete(id: number): Promise<boolean> {
    const result = await query('DELETE FROM antennas WHERE id = $1', [id]);
    return (result.rowCount || 0) > 0;
  }

  static async getBySensorId(sensorId: number): Promise<any[]> {
    const result = await query(
      `SELECT a.*, sa.port, sa.is_active
       FROM antennas a
       JOIN sensor_antennas sa ON a.id = sa.antenna_id
       WHERE sa.sensor_id = $1 AND sa.is_active = 1
       ORDER BY sa.port`,
      [sensorId]
    );
    return result.rows;
  }

  static async assignToSensor(sensorId: number, antennaId: number, port: number, userId?: number): Promise<any> {
    const result = await query(
      `INSERT INTO sensor_antennas (sensor_id, antenna_id, port, created_by)
       VALUES ($1, $2, $3, $4)
       RETURNING id`,
      [sensorId, antennaId, port, userId || null]
    );
    return { id: result.rows[0].id, sensor_id: sensorId, antenna_id: antennaId, port };
  }

  static async removeFromSensor(sensorId: number, antennaId: number): Promise<boolean> {
    const result = await query(
      `DELETE FROM sensor_antennas WHERE sensor_id = $1 AND antenna_id = $2`,
      [sensorId, antennaId]
    );
    return (result.rowCount || 0) > 0;
  }
}
