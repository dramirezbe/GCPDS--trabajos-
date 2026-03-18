import { Router, Request, Response } from 'express';
import { query } from '../database/connection';

const router = Router();

/**
 * @swagger
 * /api/config:
 *   get:
 *     summary: Obtener configuraciones del sistema
 *     tags: [Config]
 *     responses:
 *       200:
 *         description: Lista de configuraciones
 */
router.get('/', async (req: Request, res: Response) => {
  try {
    const result = await query('SELECT * FROM system_configurations');
    const configs: Record<string, string> = {};
    
    result.rows.forEach((row: any) => {
      configs[row.key] = row.value;
    });
    
    res.json(configs);
  } catch (error: any) {
    console.error('Error getting system configs:', error);
    res.status(500).json({ error: 'Error getting system configurations' });
  }
});

/**
 * @swagger
 * /api/config:
 *   post:
 *     summary: Actualizar configuraciones del sistema
 *     tags: [Config]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *     responses:
 *       200:
 *         description: Configuraciones actualizadas
 */
router.post('/', async (req: Request, res: Response) => {
  try {
    const updates = req.body;
    
    for (const [key, value] of Object.entries(updates)) {
      await query(`
        INSERT INTO system_configurations (key, value, updated_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (key) DO UPDATE SET
          value = EXCLUDED.value,
          updated_at = NOW()
      `, [key, String(value)]);
    }
    
    res.json({ message: 'Configurations updated successfully' });
  } catch (error: any) {
    console.error('Error updating system configs:', error);
    res.status(500).json({ error: 'Error updating system configurations' });
  }
});

export default router;
