import { Router, Request, Response } from 'express';
import { query, dbRun, dbGet, dbAll, getClient } from '../database/connection';
import { authenticateToken, requireAdmin, AuthRequest } from '../middleware/auth';

const router = Router();

/**
 * @swagger
 * /api/campaigns/statistics/summary:
 *   get:
 *     summary: Obtener estadísticas generales de campañas y sensores
 *     description: Retorna contadores agrupados por estado para campañas y sensores
 *     tags: [Campaigns]
 *     responses:
 *       200:
 *         description: Estadísticas generales
 */
router.get('/statistics/summary', authenticateToken, async (req: any, res: Response) => {
  try {
    // Estadísticas de campañas
    const campaignStatsResult = await query(`
      SELECT 
        status,
        COUNT(*) as count
      FROM campaigns
      GROUP BY status
    `);

    // Estadísticas de sensores
    const sensorStatsResult = await query(`
      SELECT 
        status,
        COUNT(*) as count
      FROM sensors
      GROUP BY status
    `);

    // Total de campañas
    const totalCampaignsResult = await query(`
      SELECT COUNT(*) as total FROM campaigns
    `);

    // Total de sensores
    const totalSensorsResult = await query(`
      SELECT COUNT(*) as total FROM sensors
    `);

    // Formatear las estadísticas de campañas
    const campaignStats = {
      total: parseInt(totalCampaignsResult.rows[0]?.total || '0'),
      scheduled: 0,
      running: 0,
      completed: 0,
      cancelled: 0
    };

    campaignStatsResult.rows.forEach((row: any) => {
      const count = parseInt(row.count);
      switch (row.status) {
        case 'scheduled':
          campaignStats.scheduled = count;
          break;
        case 'running':
          campaignStats.running = count;
          break;
        case 'completed':
          campaignStats.completed = count;
          break;
        case 'cancelled':
          campaignStats.cancelled = count;
          break;
      }
    });

    // Formatear las estadísticas de sensores
    const sensorStats = {
      total: parseInt(totalSensorsResult.rows[0]?.total || '0'),
      active: 0,
      inactive: 0,
      error: 0
    };

    sensorStatsResult.rows.forEach((row: any) => {
      const count = parseInt(row.count);
      switch (row.status) {
        case 'active':
          sensorStats.active = count;
          break;
        case 'inactive':
          sensorStats.inactive = count;
          break;
        case 'error':
          sensorStats.error = count;
          break;
      }
    });

    res.json({
      campaigns: campaignStats,
      sensors: sensorStats
    });
  } catch (error: any) {
    console.error('Error fetching statistics:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/campaigns:
 *   get:
 *     summary: Obtener todas las campañas
 *     description: Lista todas las campañas de medición configuradas
 *     tags: [Campaigns]
 *     responses:
 *       200:
 *         description: Lista de campañas
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 $ref: '#/components/schemas/Campaign'
 */
router.get('/', authenticateToken, async (req: any, res: Response) => {
  try {
    const campaignsResult = await query(`
      SELECT 
        c.*,
        u.full_name as created_by_name,
        COUNT(DISTINCT cs.sensor_mac) as devices
      FROM campaigns c
      LEFT JOIN campaign_sensors cs ON c.id = cs.campaign_id
      LEFT JOIN users u ON c.created_by = u.id
      GROUP BY c.id, c.name, c.description, c.status, c.start_date, c.end_date, 
               c.start_time, c.end_time, c.interval_seconds, c.start_freq_mhz, 
               c.end_freq_mhz, c.bandwidth_mhz, c.resolution_khz, c.preset, 
               c.config, c.created_at, c.updated_at, u.full_name
      ORDER BY c.created_at DESC
    `);

    // Obtener sensores de cada campaña con nombres y GPS
    const campaignsWithSensors = await Promise.all(
      campaignsResult.rows.map(async (campaign: any) => {
        const sensorsResult = await query(`
          SELECT s.mac, s.name, s.lat, s.lng 
          FROM campaign_sensors cs
          JOIN sensors s ON cs.sensor_mac = s.mac
          WHERE cs.campaign_id = $1
        `, [campaign.id]);

        const sensors = sensorsResult.rows.map((s: any) => s.mac);
        const sensorNames = sensorsResult.rows.map((s: any) => s.name);
        
        let gpsCoordinates = sensorsResult.rows.map((s: any) => ({
          mac: s.mac,
          lat: parseFloat(s.lat),
          lng: parseFloat(s.lng)
        }));

        // Si hay GPS manual en la configuración de la campaña, sobrescribir
        if (campaign.config) {
          let configObj = campaign.config;
          if (typeof configObj === 'string') {
            try {
              configObj = JSON.parse(configObj);
            } catch (e) {
              // Ignore error
            }
          }

          if (configObj.gps && (configObj.gps.lat !== undefined) && (configObj.gps.lng !== undefined)) {
             gpsCoordinates = sensorsResult.rows.map((s: any) => ({
                mac: s.mac,
                lat: parseFloat(configObj.gps.lat),
                lng: parseFloat(configObj.gps.lng)
             }));
          }
        }

        return {
          ...campaign,
          sensors,
          sensor_names: sensorNames,
          gps_coordinates: gpsCoordinates
        };
      })
    );

    res.json(campaignsWithSensors);
  } catch (error: any) {
    console.error('Error fetching campaigns:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/campaigns/{id}:
 *   get:
 *     summary: Obtener campaña específica
 *     description: Consulta los detalles completos de una campaña
 *     tags: [Campaigns]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *     responses:
 *       200:
 *         description: Campaña encontrada
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Campaign'
 *       404:
 *         description: Campaña no encontrada
 */
router.get('/:id', authenticateToken, async (req: any, res: Response) => {
  try {
    const campaignResult = await query(`
      SELECT c.*, COUNT(DISTINCT cs.sensor_mac) as devices
      FROM campaigns c
      LEFT JOIN campaign_sensors cs ON c.id = cs.campaign_id
      WHERE c.id = $1
      GROUP BY c.id, c.name, c.description, c.status, c.start_date, c.end_date, 
               c.start_time, c.end_time, c.interval_seconds, c.start_freq_mhz, 
               c.end_freq_mhz, c.bandwidth_mhz, c.resolution_khz, c.preset, 
               c.config, c.created_at, c.updated_at
    `, [req.params.id]);

    if (campaignResult.rows.length === 0) {
      return res.status(404).json({ error: 'Campaign not found' });
    }

    const campaign = campaignResult.rows[0];

    const sensorsResult = await query(`
      SELECT sensor_mac 
      FROM campaign_sensors 
      WHERE campaign_id = $1
    `, [req.params.id]);

    res.json({
      ...campaign,
      sensors: sensorsResult.rows.map((s: any) => s.sensor_mac)
    });
  } catch (error: any) {
    console.error('Error fetching campaign:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/campaigns:
 *   post:
 *     summary: Crear nueva campaña
 *     description: Crea una nueva campaña de medición con sensores asignados
 *     tags: [Campaigns]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - name
 *               - start_date
 *               - end_date
 *               - sensors
 *             properties:
 *               name:
 *                 type: string
 *                 example: Monitoreo FM Bogotá
 *               description:
 *                 type: string
 *               start_date:
 *                 type: string
 *                 format: date
 *                 example: "2025-01-01"
 *               end_date:
 *                 type: string
 *                 format: date
 *                 example: "2025-01-31"
 *               start_time:
 *                 type: string
 *                 example: "08:00"
 *               end_time:
 *                 type: string
 *                 example: "18:00"
 *               interval_seconds:
 *                 type: integer
 *                 example: 300
 *               start_freq_mhz:
 *                 type: number
 *                 example: 88.0
 *               end_freq_mhz:
 *                 type: number
 *                 example: 108.0
 *               bandwidth_mhz:
 *                 type: number
 *                 example: 0.2
 *               resolution_khz:
 *                 type: number
 *                 example: 10
 *               preset:
 *                 type: string
 *                 example: FM_BROADCAST
 *               sensors:
 *                 type: array
 *                 items:
 *                   type: string
 *                 example: ["00:11:22:33:44:55"]
 *     responses:
 *       201:
 *         description: Campaña creada
 *       400:
 *         description: Datos inválidos
 */
router.post('/', authenticateToken, async (req: any, res: Response) => {
  const client = await getClient();
  try {
    // Validar que el usuario esté autenticado
    if (!req.user || !req.user.id) {
      return res.status(401).json({ 
        error: 'Usuario no autenticado. Por favor, inicie sesión nuevamente.' 
      });
    }

    const {
      name,
      start_date,
      end_date,
      start_time,
      end_time,
      interval_seconds,
      start_freq_mhz,
      end_freq_mhz,
      bandwidth_mhz,
      resolution_khz,
      sensors,
      preset,
      config
    } = req.body;

    // Validaciones básicas
    if (!name || !start_date || !end_date || !sensors || sensors.length === 0) {
      return res.status(400).json({ 
        error: 'Missing required fields: name, start_date, end_date, sensors' 
      });
    }

    // Validar conflictos de horario con campañas existentes
    const conflictingCampaigns = await client.query(`
      SELECT c.name, cs.sensor_mac
      FROM campaigns c
      JOIN campaign_sensors cs ON c.id = cs.campaign_id
      WHERE c.status = 'scheduled'
      AND cs.sensor_mac = ANY($1)
      AND c.start_date <= $3 
      AND c.end_date >= $2
      AND c.start_time <= $5 
      AND c.end_time >= $4
    `, [
      sensors,
      start_date,
      end_date,
      start_time,
      end_time
    ]);

    if (conflictingCampaigns.rows.length > 0) {
      const conflict = conflictingCampaigns.rows[0];
      return res.status(409).json({ 
        error: `El sensor ${conflict.sensor_mac} ya está programado en la campaña '${conflict.name}' que coincide con el horario seleccionado.`
      });
    }

    // Validación adicional: Verificar estado actual de sensores si la campaña inicia pronto (< 5 min)
    const now = new Date();
    // Construir fecha de inicio combinando fecha y hora
    const startDateTimeStr = `${start_date}T${start_time || '00:00:00'}`;
    const campaignStart = new Date(startDateTimeStr);
    
    // Diferencia en milisegundos
    const timeDiff = campaignStart.getTime() - now.getTime();

    // Mínimo 3 minutos de margen para calibración del sensor
    if (timeDiff >= 0 && timeDiff < 3 * 60 * 1000) {
      return res.status(400).json({
        error: 'La campaña debe programarse con al menos 3 minutos de anticipación para permitir la calibración de los sensores.'
      });
    }
    
    // Si la campaña inicia en el pasado (ya) o en menos de 5 minutos
    if (timeDiff < 5 * 60 * 1000) {
      // Verificar estado actual de los sensores
      const busySensorsResult = await client.query(`
        SELECT name, mac, status 
        FROM sensors 
        WHERE mac = ANY($1) 
        AND (status = 'busy' OR status = 'error')
      `, [sensors]);

      if (busySensorsResult.rows.length > 0) {
        const busySensor = busySensorsResult.rows[0];
        return res.status(409).json({ 
          error: `No se puede iniciar la campaña: El sensor ${busySensor.name} (${busySensor.mac}) está actualmente en estado '${busySensor.status}'.` 
        });
      }
    }

    // DEBUG: Log valores recibidos
    console.log('🆕 Creating campaign with values:');
    console.log(`  start_freq_mhz: ${start_freq_mhz}`);
    console.log(`  end_freq_mhz: ${end_freq_mhz}`);
    console.log(`  config:`, config);

    // Asegurar que config tenga center_freq_hz en Hz para compatibilidad con sensores
    let enrichedConfig = config ? { ...config } : {};
    if (enrichedConfig.centerFrequency && !enrichedConfig.center_freq_hz) {
      enrichedConfig.center_freq_hz = Math.round(enrichedConfig.centerFrequency * 1e6);
      console.log(`  ✅ Added center_freq_hz to config: ${enrichedConfig.center_freq_hz} Hz`);
    }

    await client.query('BEGIN');

    // Insertar campaña con el usuario que la creó
    const result = await client.query(`
      INSERT INTO campaigns (
        name, status, start_date, end_date, start_time, end_time,
        interval_seconds, start_freq_mhz, end_freq_mhz, 
        bandwidth_mhz, resolution_khz, preset, config, created_by
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
      RETURNING id
    `, [
      name,
      'scheduled',
      start_date,
      end_date,
      start_time,
      end_time,
      interval_seconds,
      start_freq_mhz,
      end_freq_mhz,
      bandwidth_mhz,
      resolution_khz,
      preset,
      JSON.stringify(enrichedConfig),
      req.user?.id // ID del usuario autenticado
    ]);

    const campaignId = result.rows[0].id;

    // Insertar sensores asociados
    for (const sensorMac of sensors) {
      await client.query(`
        INSERT INTO campaign_sensors (campaign_id, sensor_mac)
        VALUES ($1, $2)
      `, [campaignId, sensorMac]);
    }

    await client.query('COMMIT');

    res.status(201).json({
      id: campaignId,
      message: 'Campaign created successfully'
    });
  } catch (error: any) {
    await client.query('ROLLBACK');
    console.error('Error creating campaign:', error);
    res.status(500).json({ error: error.message });
  } finally {
    client.release();
  }
});

/**
 * @swagger
 * /api/campaigns/{id}:
 *   put:
 *     summary: Actualizar campaña
 *     description: Modifica los datos de una campaña existente
 *     tags: [Campaigns]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *     requestBody:
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               name:
 *                 type: string
 *               status:
 *                 type: string
 *               start_date:
 *                 type: string
 *               end_date:
 *                 type: string
 *               sensors:
 *                 type: array
 *                 items:
 *                   type: string
 *     responses:
 *       200:
 *         description: Campaña actualizada
 */
router.put('/:id', authenticateToken, async (req: any, res: Response) => {
  const client = await getClient();
  try {
    const {
      name,
      status,
      start_date,
      end_date,
      start_time,
      end_time,
      interval_seconds,
      start_freq_mhz,
      end_freq_mhz,
      bandwidth_mhz,
      resolution_khz,
      preset,
      config,
      sensors
    } = req.body;

    // Validar estado si se proporciona
    const validStatuses = ['scheduled', 'running', 'completed', 'cancelled'];
    if (status && !validStatuses.includes(status)) {
      return res.status(400).json({ 
        error: `Invalid status. Must be one of: ${validStatuses.join(', ')}` 
      });
    }

    await client.query('BEGIN');

    await client.query(`
      UPDATE campaigns SET
        name = $1,
        status = $2,
        start_date = $3,
        end_date = $4,
        start_time = $5,
        end_time = $6,
        interval_seconds = $7,
        start_freq_mhz = $8,
        end_freq_mhz = $9,
        bandwidth_mhz = $10,
        resolution_khz = $11,
        preset = $12,
        config = $13,
        updated_at = NOW(),
        updated_by = $14
      WHERE id = $15
    `, [
      name,
      status,
      start_date,
      end_date,
      start_time,
      end_time,
      interval_seconds,
      start_freq_mhz,
      end_freq_mhz,
      bandwidth_mhz,
      resolution_khz,
      preset,
      config ? JSON.stringify(config) : null,
      req.user?.id,
      req.params.id
    ]);

    // Actualizar sensores si se proporcionan
    if (sensors) {
      // Eliminar sensores existentes
      await client.query('DELETE FROM campaign_sensors WHERE campaign_id = $1', [req.params.id]);

      // Insertar nuevos sensores
      for (const sensorMac of sensors) {
        await client.query(`
          INSERT INTO campaign_sensors (campaign_id, sensor_mac)
          VALUES ($1, $2)
        `, [req.params.id, sensorMac]);
      }
    }

    await client.query('COMMIT');

    res.json({ message: 'Campaign updated successfully' });
  } catch (error: any) {
    await client.query('ROLLBACK');
    console.error('Error updating campaign:', error);
    res.status(500).json({ error: error.message });
  } finally {
    client.release();
  }
});

/**
 * @swagger
 * /api/campaigns/{id}:
 *   delete:
 *     summary: Eliminar campaña
 *     description: Elimina una campaña del sistema
 *     tags: [Campaigns]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *     responses:
 *       200:
 *         description: Campaña eliminada
 */
router.delete('/:id', authenticateToken, requireAdmin, async (req: any, res: Response) => {
  const client = await getClient();
  try {
    await client.query('BEGIN');
    
    // Eliminar sensores asociados (ON DELETE CASCADE debería hacerlo automáticamente)
    await client.query('DELETE FROM campaign_sensors WHERE campaign_id = $1', [req.params.id]);
    
    // Eliminar campaña
    await client.query('DELETE FROM campaigns WHERE id = $1', [req.params.id]);

    await client.query('COMMIT');

    res.json({ message: 'Campaign deleted successfully' });
  } catch (error: any) {
    await client.query('ROLLBACK');
    console.error('Error deleting campaign:', error);
    res.status(500).json({ error: error.message });
  } finally {
    client.release();
  }
});

/**
 * @swagger
 * /api/campaigns/{id}/start:
 *   post:
 *     summary: Iniciar campaña
 *     description: Cambia el estado de la campaña a 'running'
 *     tags: [Campaigns]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *     responses:
 *       200:
 *         description: Campaña iniciada
 */
router.post('/:id/start', authenticateToken, async (req: any, res: Response) => {
  try {
    await query(`
      UPDATE campaigns 
      SET status = 'running', updated_at = NOW(), updated_by = $2
      WHERE id = $1
    `, [req.params.id, req.user?.id]);

    // Actualizar estado de sensores a 'busy'
    const sensors = await query(
      'SELECT sensor_mac FROM campaign_sensors WHERE campaign_id = $1',
      [req.params.id]
    );
    for (const sensor of sensors.rows) {
      const { SensorModel } = require('../models/Sensor');
      await SensorModel.updateStatus(sensor.sensor_mac, 'busy');
      console.log(`⚡ Sensor ${sensor.sensor_mac} updated to BUSY (Campaign ${req.params.id} manually started)`);
    }

    res.json({ message: 'Campaign started successfully' });
  } catch (error: any) {
    console.error('Error starting campaign:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/campaigns/{id}/stop:
 *   post:
 *     summary: Detener campaña
 *     description: Cambia el estado de la campaña a 'completed'
 *     tags: [Campaigns]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *     responses:
 *       200:
 *         description: Campaña detenida
 */
router.post('/:id/stop', authenticateToken, requireAdmin, async (req: any, res: Response) => {
  try {
    await query(`
      UPDATE campaigns 
      SET status = 'completed', updated_at = NOW(), updated_by = $2
      WHERE id = $1
    `, [req.params.id, req.user?.id]);

    // Actualizar estado de sensores a 'online'
    const sensors = await query(
      'SELECT sensor_mac FROM campaign_sensors WHERE campaign_id = $1',
      [req.params.id]
    );
    for (const sensor of sensors.rows) {
      const { SensorModel } = require('../models/Sensor');
      await SensorModel.updateStatus(sensor.sensor_mac, 'online');
      console.log(`⚡ Sensor ${sensor.sensor_mac} updated to ONLINE (Campaign ${req.params.id} manually stopped)`);
    }

    res.json({ message: 'Campaign stopped successfully' });
  } catch (error: any) {
    console.error('Error stopping campaign:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/campaigns/{id}/data:
 *   get:
 *     summary: Obtener datos de mediciones de una campaña
 *     description: Consulta las mediciones capturadas durante una campaña para un sensor específico
 *     tags: [Campaigns]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *       - in: query
 *         name: sensor_mac
 *         required: true
 *         schema:
 *           type: string
 *         description: Dirección MAC del sensor
 *         example: "00:11:22:33:44:55"
 *     responses:
 *       200:
 *         description: Datos de la campaña
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 campaign:
 *                   $ref: '#/components/schemas/Campaign'
 *                 measurements:
 *                   type: array
 *                   items:
 *                     $ref: '#/components/schemas/SensorData'
 *                 totalMeasurements:
 *                   type: integer
 *       400:
 *         description: Parámetro sensor_mac requerido
 *       404:
 *         description: Campaña no encontrada
 */
router.get('/:id/data', authenticateToken, async (req: any, res: Response) => {
  try {
    const campaignId = req.params.id;
    const sensorMac = req.query.sensor_mac as string;
    const limit = req.query.limit ? parseInt(req.query.limit as string) : 5000; // Aumentado default a 5000 para ver campañas completas

    if (!sensorMac) {
      return res.status(400).json({ error: 'sensor_mac query parameter is required' });
    }

    // Obtener mediciones de la campaña para el sensor específico
    const measurementsResult = await query(`
      SELECT 
        id,
        mac,
        campaign_id,
        pxx,
        start_freq_hz,
        end_freq_hz,
        timestamp,
        lat,
        lng,
        excursion_peak_to_peak_hz,
        excursion_peak_deviation_hz,
        excursion_rms_deviation_hz,
        depth_peak_to_peak,
        depth_peak_deviation,
        depth_rms_deviation,
        created_at
      FROM sensor_data
      WHERE campaign_id = $1 AND mac = $2
      ORDER BY timestamp ASC
      LIMIT $3
    `, [campaignId, sensorMac, limit]);

    // Obtener información de la campaña
    const campaignResult = await query(`
      SELECT * FROM campaigns WHERE id = $1
    `, [campaignId]);

    if (campaignResult.rows.length === 0) {
      return res.status(404).json({ error: 'Campaign not found' });
    }

    res.json({
      campaign: campaignResult.rows[0],
      measurements: measurementsResult.rows,
      totalMeasurements: measurementsResult.rows.length
    });
  } catch (error: any) {
    console.error('Error fetching campaign data:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * Función auxiliar para actualizar automáticamente el estado de las campañas
 * basándose en las fechas y horas actuales
 */
async function updateCampaignStatuses() {
  try {
    // 1. Cambiar 'scheduled' a 'running' si la fecha/hora de inicio ha llegado
    // Comparamos directamente con NOW() usando TIMESTAMP en la zona horaria local de Bogotá
    const runningCampaigns = await query(`
      UPDATE campaigns
      SET status = 'running', updated_at = NOW()
      WHERE status = 'scheduled'
        AND ((start_date + COALESCE(start_time, '00:00:00')::time) AT TIME ZONE 'America/Bogota') <= NOW()
      RETURNING id
    `);

    // Actualizar estado de sensores a 'busy' para campañas que acaban de iniciar
    if (runningCampaigns.rows.length > 0) {
      for (const campaign of runningCampaigns.rows) {
        const sensors = await query(
          'SELECT sensor_mac FROM campaign_sensors WHERE campaign_id = $1',
          [campaign.id]
        );
        for (const sensor of sensors.rows) {
          // Importar SensorModel dinámicamente para evitar dependencias circulares si las hubiera
          const { SensorModel } = require('../models/Sensor');
          await SensorModel.updateStatus(sensor.sensor_mac, 'busy');
          console.log(`⚡ Sensor ${sensor.sensor_mac} updated to BUSY (Campaign ${campaign.id} started)`);
        }
      }
    }

    // 2. Cambiar 'running' a 'completed' si la fecha/hora de fin ha pasado
    // Solo marca como completed si la fecha+hora de FIN ya pasó (en hora Bogotá)
    const completedCampaigns = await query(`
      UPDATE campaigns
      SET status = 'completed', updated_at = NOW()
      WHERE status = 'running'
        AND ((end_date + COALESCE(end_time, '23:59:59')::time) AT TIME ZONE 'America/Bogota') <= NOW()
      RETURNING id
    `);

    // Actualizar estado de sensores a 'online' para campañas que acaban de terminar
    if (completedCampaigns.rows.length > 0) {
      for (const campaign of completedCampaigns.rows) {
        const sensors = await query(
          'SELECT sensor_mac FROM campaign_sensors WHERE campaign_id = $1',
          [campaign.id]
        );
        for (const sensor of sensors.rows) {
          const { SensorModel } = require('../models/Sensor');
          await SensorModel.updateStatus(sensor.sensor_mac, 'online');
          console.log(`⚡ Sensor ${sensor.sensor_mac} updated to ONLINE (Campaign ${campaign.id} completed)`);
        }
      }
    }

    console.log(`✅ Campaign statuses updated at ${new Date().toISOString()}`);
  } catch (error) {
    console.error('❌ Error updating campaign statuses:', error);
  }
}

/**
 * @swagger
 * /api/campaigns/update-statuses:
 *   post:
 *     summary: Actualizar estados de campañas
 *     description: Actualiza automáticamente los estados de las campañas según fechas y horas
 *     tags: [Campaigns]
 *     responses:
 *       200:
 *         description: Estados actualizados
 */
router.post('/update-statuses', authenticateToken, async (req: any, res: Response) => {
  try {
    await updateCampaignStatuses();
    res.json({ message: 'Campaign statuses updated successfully' });
  } catch (error: any) {
    console.error('Error updating campaign statuses:', error);
    res.status(500).json({ error: error.message });
  }
});

// Ejecutar actualización automática cada 1 minuto
setInterval(updateCampaignStatuses, 60000);

// Ejecutar una vez al inicio
updateCampaignStatuses();

export default router;
