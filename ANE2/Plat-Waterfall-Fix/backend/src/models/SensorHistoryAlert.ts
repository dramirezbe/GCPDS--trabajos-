import { query } from '../database/connection';

export interface SensorHistoryAlert {
  id?: number;
  sensor_mac: string;
  alert_type: string;
  description: string;
  timestamp: number;
  created_at?: number;
}

export class SensorHistoryAlertModel {
  static async create(alert: SensorHistoryAlert): Promise<SensorHistoryAlert> {
    const result = await query(
      `INSERT INTO sensor_history_alert (sensor_mac, alert_type, description, timestamp)
       VALUES ($1, $2, $3, $4)
       RETURNING *`,
      [alert.sensor_mac, alert.alert_type, alert.description, alert.timestamp]
    );
    return result.rows[0];
  }

  static async shouldCreateAlert(sensor_mac: string, alert_type: string, timeoutMinutes: number = 30): Promise<boolean> {
    const timeoutMs = timeoutMinutes * 60 * 1000;
    const thresholdTime = Date.now() - timeoutMs;
    
    const result = await query(
      `SELECT id FROM sensor_history_alert 
       WHERE sensor_mac = $1 AND alert_type = $2 AND timestamp > $3
       LIMIT 1`,
      [sensor_mac, alert_type, thresholdTime]
    );
    
    return result.rows.length === 0;
  }

  static async getHistory(filters: { 
    startDate?: number, 
    endDate?: number, 
    sensor_mac?: string,
    limit?: number,
    offset?: number
  }): Promise<{ alerts: SensorHistoryAlert[], total: number }> {
    const conditions: string[] = [];
    const values: any[] = [];
    let paramIndex = 1;

    if (filters.startDate) {
      conditions.push(`timestamp >= $${paramIndex++}`);
      values.push(filters.startDate);
    }

    if (filters.endDate) {
      conditions.push(`timestamp <= $${paramIndex++}`);
      values.push(filters.endDate);
    }

    if (filters.sensor_mac) {
      conditions.push(`sensor_mac = $${paramIndex++}`);
      values.push(filters.sensor_mac);
    }

    const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
    
    // Get total count
    const countResult = await query(
      `SELECT COUNT(*) as total FROM sensor_history_alert ${whereClause}`,
      values
    );
    const total = parseInt(countResult.rows[0].total);

    // Get alerts with pagination
    const limit = filters.limit || 50;
    const offset = filters.offset || 0;
    
    const alertsResult = await query(
      `SELECT * FROM sensor_history_alert 
       ${whereClause} 
       ORDER BY timestamp DESC 
       LIMIT $${paramIndex++} OFFSET $${paramIndex}`,
      [...values, limit, offset]
    );

    return {
      alerts: alertsResult.rows.map(row => ({
        ...row,
        timestamp: parseInt(row.timestamp),
        created_at: parseInt(row.created_at)
      })),
      total
    };
  }
}
