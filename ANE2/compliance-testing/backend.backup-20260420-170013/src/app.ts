import express, { Request, Response } from 'express';
import cors from 'cors';
import http from 'http';
import dotenv from 'dotenv';
import { initDatabase } from './database/migrate-postgres';
import { initWebSocket, broadcastToClients } from './websocket';
import { setupSwagger } from './swagger';
import { setupAudioWebSocket, getAudioServerStatus } from './audioServer';
import { SensorModel } from './models/Sensor';
import managementRoutes from './routes/management';
import sensorRoutes from './routes/sensor';
import campaignRoutes from './routes/campaign';
import reportsRoutes from './routes/reports';
import authRoutes from './routes/auth';
import configRoutes from './routes/config';

// Cargar variables de entorno
dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Logging middleware
app.use((req: Request, res: Response, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
  next();
});

// Inicializar base de datos
initDatabase().catch(err => {
  console.error('❌ Error initializing database:', err);
});

// Configurar Swagger
setupSwagger(app);

/**
 * @swagger
 * /:
 *   get:
 *     summary: Información de la API
 *     description: Endpoint raíz que devuelve información básica sobre la API y sus endpoints
 *     tags: [System]
 *     responses:
 *       200:
 *         description: Información de la API
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 message:
 *                   type: string
 *                   example: ANE Backend API
 *                 version:
 *                   type: string
 *                   example: 1.0.0
 *                 endpoints:
 *                   type: object
 *                   properties:
 *                     sensors:
 *                       type: string
 *                       example: /api/sensors
 *                     antennas:
 *                       type: string
 *                       example: /api/antennas
 *                     sensor_data:
 *                       type: string
 *                       example: /api/sensor
 *                     websocket:
 *                       type: string
 *                       example: ws://localhost:3000/ws
 *                     documentation:
 *                       type: string
 *                       example: /api-docs
 */
app.get('/', (req: Request, res: Response) => {
  res.json({
    message: 'ANE Backend API',
    version: '1.0.0',
    endpoints: {
      sensors: '/api/sensors',
      antennas: '/api/antennas',
      sensor_data: '/api/sensor',
      websocket: 'ws://localhost:' + PORT + '/ws',
      documentation: '/api-docs'
    }
  });
});

// Rutas de API
app.use('/api/auth', authRoutes);
app.use('/api/sensor', sensorRoutes);
app.use('/api/campaigns', campaignRoutes);
app.use('/api/reports', reportsRoutes);
app.use('/api/config', configRoutes);
app.use('/api', managementRoutes); // Mover al final para evitar conflictos de enrutamiento

// Audio server status endpoint
app.get('/api/audio/status', (req: Request, res: Response) => {
  res.json(getAudioServerStatus());
});

// Manejo de errores 404
app.use((req: Request, res: Response) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

// Manejo de errores global
app.use((err: any, req: Request, res: Response, next: any) => {
  console.error('Error:', err);
  res.status(500).json({ error: 'Internal server error', message: err.message });
});

// Crear servidor HTTP
const server = http.createServer(app);

// Aumentar timeout del servidor a 1 hora (3600000 ms)
// para permitir reportes extremadamente largos
server.setTimeout(3600000);

// Inicializar WebSocket para datos de sensores
initWebSocket(server);

// Inicializar WebSocket para streaming de audio
setupAudioWebSocket(server);

// Schedule Sensor Status Validation (every 30 seconds)
setInterval(async () => {
  try {
    const result = await SensorModel.validateAndUpdateStatus();
    // Notificar al frontend si hubo cambios de estado
    if (result.updated > 0) {
      broadcastToClients({
        type: 'sensor_status_changed',
        sensors: result.sensors,
        timestamp: Date.now()
      });
    }
  } catch (err) {
    console.error('Error validating sensor status:', err);
  }
}, 30000);

// Iniciar servidor
server.listen(PORT, () => {
  console.log('==========================================');
  console.log('🚀 ANE Backend Server Started');
  console.log('==========================================');
  console.log(`📡 HTTP Server: http://localhost:${PORT}`);
  console.log(`🔌 WebSocket: ws://localhost:${PORT}/ws`);  console.log(`🎵 Audio WS: ws://localhost:${PORT}/ws/audio/sensor/{id}`);
  console.log(`🎵 Audio WS: ws://localhost:${PORT}/ws/audio/listen/{id}`);  console.log(`📊 Database: PostgreSQL (${process.env.DB_HOST || 'localhost'}:${process.env.DB_PORT || '5432'}/${process.env.DB_NAME || 'ane_db'})`);
  console.log('==========================================');
});

// Manejo de señales de terminación
process.on('SIGTERM', () => {
  console.log('SIGTERM received, closing server...');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('\nSIGINT received, closing server...');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

export default app;
