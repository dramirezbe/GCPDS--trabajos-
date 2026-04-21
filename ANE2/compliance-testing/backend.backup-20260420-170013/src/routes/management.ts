import { Router, Request, Response } from 'express';
import { SensorModel } from '../models/Sensor';
import { AntennaModel } from '../models/Antenna';
import { SensorHistoryAlertModel } from '../models/SensorHistoryAlert';
import { authenticateToken, requireAdmin, AuthRequest } from '../middleware/auth';

const router = Router();

// ========== SENSORES ==========

/**
 * @swagger
 * /api/sensors:
 *   get:
 *     summary: Obtener todos los sensores
 *     description: Lista todos los sensores registrados en el sistema
 *     tags: [Sensors Management]
 *     responses:
 *       200:
 *         description: Lista de sensores
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 $ref: '#/components/schemas/Sensor'
 *       500:
 *         description: Error del servidor
 */
router.get('/sensors', async (req: Request, res: Response) => {
  try {
    const sensors = await SensorModel.getAll();
    res.json(sensors);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensors/{id}:
 *   get:
 *     summary: Obtener sensor por ID
 *     description: Consulta un sensor específico por su ID
 *     tags: [Sensors Management]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *         description: ID del sensor
 *     responses:
 *       200:
 *         description: Sensor encontrado
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Sensor'
 *       404:
 *         description: Sensor no encontrado
 */
router.get('/sensors/:id', async (req: Request, res: Response) => {
  try {
    const id = Number(req.params.id);
    if (isNaN(id)) {
      return res.status(400).json({ error: 'Invalid ID format. Must be an integer.' });
    }
    const sensor = await SensorModel.getById(id);
    if (!sensor) {
      return res.status(404).json({ error: 'Sensor not found' });
    }
    res.json(sensor);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensors/mac/{mac}:
 *   get:
 *     summary: Obtener sensor por dirección MAC
 *     description: Busca un sensor por su dirección MAC única
 *     tags: [Sensors Management]
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
 *         description: Sensor encontrado
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Sensor'
 *       404:
 *         description: Sensor no encontrado
 */
router.get('/sensors/mac/:mac', async (req: Request, res: Response) => {
  try {
    const sensor = await SensorModel.getByMac(req.params.mac);
    if (!sensor) {
      return res.status(404).json({ error: 'Sensor not found' });
    }
    res.json(sensor);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensors:
 *   post:
 *     summary: Crear nuevo sensor
 *     description: Registra un nuevo sensor en el sistema
 *     tags: [Sensors Management]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - name
 *               - mac
 *             properties:
 *               name:
 *                 type: string
 *                 example: Sensor Bogotá Centro
 *               mac:
 *                 type: string
 *                 example: "00:11:22:33:44:55"
 *               lat:
 *                 type: number
 *                 example: 4.711
 *               lng:
 *                 type: number
 *                 example: -74.0721
 *               alt:
 *                 type: number
 *                 example: 2640
 *     responses:
 *       201:
 *         description: Sensor creado
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Sensor'
 *       400:
 *         description: Datos inválidos
 */
router.post('/sensors', authenticateToken, requireAdmin, async (req: any, res: Response) => {
  try {
    const sensor = await SensorModel.create(req.body, req.user?.id);
    res.status(201).json(sensor);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensors/{id}:
 *   put:
 *     summary: Actualizar sensor
 *     description: Modifica los datos de un sensor existente
 *     tags: [Sensors Management]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               name:
 *                 type: string
 *               mac:
 *                 type: string
 *               lat:
 *                 type: number
 *               lng:
 *                 type: number
 *               alt:
 *                 type: number
 *               status:
 *                 type: string
 *     responses:
 *       200:
 *         description: Sensor actualizado
 *       404:
 *         description: Sensor no encontrado
 */
router.put('/sensors/:id', authenticateToken, async (req: any, res: Response) => {
  try {
    const sensor = await SensorModel.update(Number(req.params.id), req.body, req.user?.id);
    if (!sensor) {
      return res.status(404).json({ error: 'Sensor not found' });
    }
    res.json(sensor);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensors/{id}:
 *   delete:
 *     summary: Eliminar sensor
 *     description: Elimina un sensor del sistema
 *     tags: [Sensors Management]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *     responses:
 *       204:
 *         description: Sensor eliminado
 *       404:
 *         description: Sensor no encontrado
 */
router.delete('/sensors/:id', async (req: Request, res: Response) => {
  try {
    const success = await SensorModel.delete(Number(req.params.id));
    if (!success) {
      return res.status(404).json({ error: 'Sensor not found' });
    }
    res.status(204).send();
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensors/validate-status:
 *   post:
 *     summary: Validar y actualizar estados de sensores
     *     description: Revisa todos los sensores y actualiza su estado a 'inactive' si no han enviado datos en más de 1 minuto
 *     tags: [Sensors Management]
 *     responses:
 *       200:
 *         description: Estados actualizados
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 updated:
 *                   type: integer
 *                   description: Número de sensores actualizados
 *                 sensors:
 *                   type: array
 *                   items:
 *                     type: object
 *                     properties:
 *                       mac:
 *                         type: string
 *                       name:
 *                         type: string
 *                       previousStatus:
 *                         type: string
 *                       newStatus:
 *                         type: string
 *                       lastUpdate:
 *                         type: integer
 *       500:
 *         description: Error del servidor
 */
router.post('/sensors/validate-status', async (req: Request, res: Response) => {
  try {
    const result = await SensorModel.validateAndUpdateStatus();
    res.json(result);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensors/{id}/antennas:
 *   get:
 *     summary: Obtener antenas asignadas a un sensor
 *     description: Lista todas las antenas conectadas a un sensor específico
 *     tags: [Sensors Management]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *     responses:
 *       200:
 *         description: Lista de antenas
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 $ref: '#/components/schemas/Antenna'
 */
router.get('/sensors/:id/antennas', async (req: Request, res: Response) => {
  try {
    const antennas = await AntennaModel.getBySensorId(Number(req.params.id));
    res.json(antennas);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensors/{id}/antennas:
 *   post:
 *     summary: Asignar antena a sensor
 *     description: Conecta una antena a un puerto específico de un sensor
 *     tags: [Sensors Management]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - antenna_id
 *               - port
 *             properties:
 *               antenna_id:
 *                 type: integer
 *                 example: 1
 *               port:
 *                 type: integer
 *                 example: 1
 *                 description: Puerto del sensor (1-4)
 *     responses:
 *       201:
 *         description: Antena asignada
 *       400:
 *         description: Datos inválidos
 */
router.post('/sensors/:id/antennas', authenticateToken, async (req: any, res: Response) => {
  try {
    const { antenna_id, port } = req.body;
    const result = await AntennaModel.assignToSensor(Number(req.params.id), antenna_id, port, req.user?.id);
    res.status(201).json(result);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/sensors/{sensorId}/antennas/{antennaId}:
 *   delete:
 *     summary: Desasignar antena de sensor
 *     description: Desconecta una antena de un sensor
 *     tags: [Sensors Management]
 *     parameters:
 *       - in: path
 *         name: sensorId
 *         required: true
 *         schema:
 *           type: integer
 *       - in: path
 *         name: antennaId
 *         required: true
 *         schema:
 *           type: integer
 *     responses:
 *       204:
 *         description: Antena desasignada
 *       404:
 *         description: Asignación no encontrada
 */
router.delete('/sensors/:sensorId/antennas/:antennaId', async (req: Request, res: Response) => {
  try {
    const success = await AntennaModel.removeFromSensor(
      Number(req.params.sensorId),
      Number(req.params.antennaId)
    );
    if (!success) {
      return res.status(404).json({ error: 'Assignment not found' });
    }
    res.status(204).send();
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// ========== ANTENAS ==========

/**
 * @swagger
 * /api/antennas:
 *   get:
 *     summary: Obtener todas las antenas
 *     description: Lista todas las antenas registradas en el sistema
 *     tags: [Antennas Management]
 *     responses:
 *       200:
 *         description: Lista de antenas
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 $ref: '#/components/schemas/Antenna'
 */
router.get('/antennas', async (req: Request, res: Response) => {
  try {
    const antennas = await AntennaModel.getAll();
    res.json(antennas);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/antennas/{id}:
 *   get:
 *     summary: Obtener antena por ID
 *     description: Consulta una antena específica por su ID
 *     tags: [Antennas Management]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *     responses:
 *       200:
 *         description: Antena encontrada
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Antenna'
 *       404:
 *         description: Antena no encontrada
 */
router.get('/antennas/:id', async (req: Request, res: Response) => {
  try {
    const antenna = await AntennaModel.getById(Number(req.params.id));
    if (!antenna) {
      return res.status(404).json({ error: 'Antenna not found' });
    }
    res.json(antenna);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/antennas:
 *   post:
 *     summary: Crear nueva antena
 *     description: Registra una nueva antena en el sistema
 *     tags: [Antennas Management]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - type
 *               - frequency_range
 *             properties:
 *               type:
 *                 type: string
 *                 example: Omnidireccional
 *               frequency_range:
 *                 type: string
 *                 example: 80-1000 MHz
 *               gain_dbi:
 *                 type: number
 *                 example: 3.5
 *               polarization:
 *                 type: string
 *                 example: Vertical
 *               vswr:
 *                 type: string
 *                 example: <2:1
 *               impedance_ohms:
 *                 type: integer
 *                 example: 50
 *     responses:
 *       201:
 *         description: Antena creada
 *       400:
 *         description: Datos inválidos
 */
router.post('/antennas', authenticateToken, async (req: any, res: Response) => {
  try {
    const antenna = await AntennaModel.create(req.body, req.user?.id);
    res.status(201).json(antenna);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/antennas/{id}:
 *   put:
 *     summary: Actualizar antena
 *     description: Modifica los datos de una antena existente
 *     tags: [Antennas Management]
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
 *               type:
 *                 type: string
 *               frequency_range:
 *                 type: string
 *               gain_dbi:
 *                 type: number
 *               polarization:
 *                 type: string
 *     responses:
 *       200:
 *         description: Antena actualizada
 *       404:
 *         description: Antena no encontrada
 */
router.put('/antennas/:id', authenticateToken, async (req: any, res: Response) => {
  try {
    const antenna = await AntennaModel.update(Number(req.params.id), req.body, req.user?.id);
    if (!antenna) {
      return res.status(404).json({ error: 'Antenna not found' });
    }
    res.json(antenna);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/antennas/{id}:
 *   delete:
 *     summary: Eliminar antena
 *     description: Elimina una antena del sistema
 *     tags: [Antennas Management]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *     responses:
 *       204:
 *         description: Antena eliminada
 *       404:
 *         description: Antena no encontrada
 */
router.delete('/antennas/:id', async (req: Request, res: Response) => {
  try {
    const success = await AntennaModel.delete(Number(req.params.id));
    if (!success) {
      return res.status(404).json({ error: 'Antenna not found' });
    }
    res.status(204).send();
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

/**
 * @swagger
 * /api/alerts:
 *   get:
 *     summary: Obtener historial de alertas
 *     tags: [Alerts]
 *     parameters:
 *       - in: query
 *         name: start_date
 *         schema:
 *           type: integer
 *       - in: query
 *         name: end_date
 *         schema:
 *           type: integer
 *       - in: query
 *         name: sensor_mac
 *         schema:
 *           type: string
 *     responses:
 *       200:
 *         description: Lista de alertas
 */
router.get('/alerts', async (req: Request, res: Response) => {
  try {
    const { start_date, end_date, sensor_mac, limit, offset } = req.query;
    
    const filters = {
      startDate: start_date ? Number(start_date) : undefined,
      endDate: end_date ? Number(end_date) : undefined,
      sensor_mac: sensor_mac as string | undefined,
      limit: limit ? Number(limit) : 50,
      offset: offset ? Number(offset) : 0
    };

    const result = await SensorHistoryAlertModel.getHistory(filters);
    res.json(result);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

export default router;
