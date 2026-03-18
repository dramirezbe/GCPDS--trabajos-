import swaggerJsdoc from 'swagger-jsdoc';
import swaggerUi from 'swagger-ui-express';
import { Express } from 'express';

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'ANE Realtime Monitoring API',
      version: '1.0.0',
      description: `
        API completa para el sistema de monitoreo en tiempo real de señales de radio de la ANE.
        
        ## Arquitectura
        - **Backend**: Node.js + Express + TypeScript
        - **Base de datos**: PostgreSQL con TimescaleDB
        - **WebSocket**: Para transmisión en tiempo real de datos de sensores
        
        ## Flujos de datos
        
        ### 1. APIs del Sensor (Envío de datos)
        Los sensores físicos envían datos a estos endpoints:
        - \`POST /api/sensor/status\` - Estado del sensor (batería, temperatura, etc.)
        - \`POST /api/sensor/gps\` - Ubicación GPS del sensor
        - \`POST /api/sensor/data\` - Datos de espectro radioeléctrico (FFT, potencia)
        - \`POST /api/sensor/audio\` - Audio demodulado (AM/FM)
        
        ### 2. APIs de Gestión (Frontend)
        El frontend utiliza estos endpoints para gestionar el sistema:
        - \`/api/sensors\` - CRUD de sensores
        - \`/api/antennas\` - CRUD de antenas
        - \`/api/campaigns\` - CRUD de campañas de medición
        - \`/api/reports\` - Generación de reportes de cumplimiento normativo
        
        ### 3. APIs de Consulta (Frontend)
        Para visualización de datos:
        - \`GET /api/sensor/:mac/latest-*\` - Últimos datos de un sensor
        - \`GET /api/sensor/:mac/data/range\` - Datos históricos por rango de tiempo
        - \`GET /api/campaigns/:id/data\` - Datos de una campaña específica
        
        ### 4. APIs de Control (Frontend → Sensor)
        Para configurar sensores remotamente:
        - \`POST /api/sensor/:mac/configure\` - Enviar configuración de escaneo
        - \`POST /api/sensor/:mac/stop\` - Detener adquisición
        - \`GET /api/sensor/:mac/configuration\` - Obtener configuración activa
      `,
      contact: {
        name: 'ANE - Agencia Nacional del Espectro',
        url: 'https://ane.gov.co'
      }
    },
    servers: [
      {
        url: 'http://localhost:3000',
        description: 'Servidor local de desarrollo'
      },
      {
        url: 'http://172.23.90.25:3000',
        description: 'Servidor de producción (VPN)'
      },
      {
        url: 'http://rsm.ane.gov.co:3000',
        description: 'Servidor de producción (Público)'
      }
    ],
    tags: [
      {
        name: 'Sensor Data',
        description: 'Endpoints para recepción de datos desde sensores físicos (POST desde dispositivos)'
      },
      {
        name: 'Sensor Query',
        description: 'Endpoints para consultar datos de sensores (GET desde frontend)'
      },
      {
        name: 'Sensor Control',
        description: 'Endpoints para configurar y controlar sensores remotamente'
      },
      {
        name: 'Sensors Management',
        description: 'CRUD de sensores - Gestión de dispositivos'
      },
      {
        name: 'Antennas Management',
        description: 'CRUD de antenas - Gestión de antenas'
      },
      {
        name: 'Campaigns',
        description: 'Gestión de campañas de medición'
      },
      {
        name: 'Reports',
        description: 'Generación de reportes de cumplimiento normativo'
      },
      {
        name: 'System',
        description: 'Información del sistema'
      }
    ],
    components: {
      schemas: {
        Sensor: {
          type: 'object',
          properties: {
            id: { type: 'integer', example: 1 },
            name: { type: 'string', example: 'Sensor Bogotá Centro' },
            mac: { type: 'string', example: '00:11:22:33:44:55' },
            lat: { type: 'number', format: 'double', example: 4.711 },
            lng: { type: 'number', format: 'double', example: -74.0721 },
            alt: { type: 'number', format: 'double', example: 2640 },
            status: { type: 'string', enum: ['active', 'inactive', 'error'], example: 'active' },
            last_seen: { type: 'integer', example: 1702745000000 },
            created_at: { type: 'string', format: 'date-time' },
            updated_at: { type: 'string', format: 'date-time' }
          }
        },
        Antenna: {
          type: 'object',
          properties: {
            id: { type: 'integer', example: 1 },
            type: { type: 'string', example: 'Omnidireccional' },
            frequency_range: { type: 'string', example: '80-1000 MHz' },
            gain_dbi: { type: 'number', example: 3.5 },
            polarization: { type: 'string', example: 'Vertical' },
            vswr: { type: 'string', example: '<2:1' },
            impedance_ohms: { type: 'integer', example: 50 },
            created_at: { type: 'string', format: 'date-time' }
          }
        },
        SensorStatus: {
          type: 'object',
          required: ['mac', 'battery', 'temperature', 'signal_quality', 'timestamp'],
          properties: {
            mac: { type: 'string', example: '00:11:22:33:44:55', description: 'Dirección MAC del sensor' },
            battery: { type: 'number', format: 'float', example: 85.5, description: 'Nivel de batería (%)' },
            temperature: { type: 'number', format: 'float', example: 28.5, description: 'Temperatura (°C)' },
            signal_quality: { type: 'number', format: 'float', example: 92.3, description: 'Calidad de señal (%)' },
            timestamp: { type: 'integer', example: 1702745000000, description: 'Timestamp Unix (ms)' }
          }
        },
        SensorGPS: {
          type: 'object',
          required: ['mac', 'lat', 'lng', 'timestamp'],
          properties: {
            mac: { type: 'string', example: '00:11:22:33:44:55' },
            lat: { type: 'number', format: 'double', example: 4.711 },
            lng: { type: 'number', format: 'double', example: -74.0721 },
            alt: { type: 'number', format: 'double', example: 2640 },
            timestamp: { type: 'integer', example: 1702745000000 }
          }
        },
        SensorData: {
          type: 'object',
          required: ['mac', 'Pxx', 'start_freq_hz', 'end_freq_hz', 'timestamp'],
          properties: {
            mac: { type: 'string', example: '00:11:22:33:44:55' },
            Pxx: { 
              type: 'array', 
              items: { type: 'number', format: 'float' },
              example: [-80.5, -82.3, -79.1],
              description: 'Array de potencias espectrales (dBm)'
            },
            start_freq_hz: { type: 'number', format: 'double', example: 88000000, description: 'Frecuencia inicial (Hz)' },
            end_freq_hz: { type: 'number', format: 'double', example: 108000000, description: 'Frecuencia final (Hz)' },
            timestamp: { type: 'integer', example: 1702745000000 },
            excursion: { type: 'number', format: 'float', example: 75000, description: 'Excursión de frecuencia FM (Hz)' },
            depth: { type: 'number', format: 'float', example: 0.85, description: 'Profundidad de modulación AM (0-1)' },
            lat: { type: 'number', format: 'double', example: 4.711 },
            lng: { type: 'number', format: 'double', example: -74.0721 },
            campaign_id: { type: 'integer', example: 1, description: 'ID de campaña asociada (opcional)' }
          }
        },
        SensorAudio: {
          type: 'object',
          required: ['mac', 'audio', 'demodType', 'timestamp'],
          properties: {
            mac: { type: 'string', example: '00:11:22:33:44:55' },
            audio: { 
              type: 'array',
              items: { type: 'number', format: 'float' },
              example: [0.1, 0.15, -0.2],
              description: 'Array de muestras de audio demodulado'
            },
            demodType: { type: 'string', enum: ['AM', 'FM'], example: 'FM' },
            timestamp: { type: 'integer', example: 1702745000000 }
          }
        },
        ScanConfiguration: {
          type: 'object',
          required: ['center_frequency', 'span', 'sample_rate_hz', 'resolution_hz', 'antenna_port'],
          properties: {
            center_frequency: { type: 'number', format: 'double', example: 98000000, description: 'Frecuencia central (Hz)' },
            span: { type: 'number', format: 'double', example: 20000000, description: 'Ancho de banda de escaneo (Hz)' },
            sample_rate_hz: { type: 'number', format: 'double', example: 2400000, description: 'Tasa de muestreo (Hz)' },
            resolution_hz: { type: 'number', format: 'double', example: 10000, description: 'Resolución espectral (Hz)' },
            antenna_port: { type: 'integer', example: 1, description: 'Puerto de antena (1-4)' },
            window: { type: 'string', enum: ['hann', 'hamming', 'blackman'], example: 'hann' },
            overlap: { type: 'number', format: 'float', example: 0.5, description: 'Solapamiento de ventanas (0-1)' }
          }
        },
        Campaign: {
          type: 'object',
          properties: {
            id: { type: 'integer', example: 1 },
            name: { type: 'string', example: 'Monitoreo FM Bogotá' },
            description: { type: 'string', example: 'Campaña de monitoreo de emisoras FM' },
            status: { type: 'string', enum: ['scheduled', 'running', 'completed', 'cancelled'], example: 'running' },
            start_date: { type: 'string', format: 'date', example: '2025-01-01' },
            end_date: { type: 'string', format: 'date', example: '2025-01-31' },
            start_time: { type: 'string', example: '08:00' },
            end_time: { type: 'string', example: '18:00' },
            interval_seconds: { type: 'integer', example: 300, description: 'Intervalo entre mediciones (segundos)' },
            start_freq_mhz: { type: 'number', example: 88.0 },
            end_freq_mhz: { type: 'number', example: 108.0 },
            bandwidth_mhz: { type: 'number', example: 0.2 },
            resolution_khz: { type: 'number', example: 10 },
            preset: { type: 'string', example: 'FM_BROADCAST' },
            sensors: { 
              type: 'array',
              items: { type: 'string' },
              example: ['00:11:22:33:44:55', '00:11:22:33:44:56']
            },
            devices: { type: 'integer', example: 2 }
          }
        },
        ComplianceReport: {
          type: 'object',
          properties: {
            campaign: { type: 'object', description: 'Información de la campaña' },
            location: {
              type: 'object',
              properties: {
                departamento: { type: 'string', example: 'Bogotá D.C.' },
                municipio: { type: 'string', example: 'Bogotá' },
                codigo_dane: { type: 'string', example: '11001' }
              }
            },
            measurements: { 
              type: 'array',
              description: 'Mediciones con análisis de cumplimiento normativo'
            }
          }
        },
        Error: {
          type: 'object',
          properties: {
            error: { type: 'string', example: 'Error description' }
          }
        },
        Success: {
          type: 'object',
          properties: {
            success: { type: 'boolean', example: true },
            message: { type: 'string', example: 'Operation completed successfully' }
          }
        }
      }
    }
  },
  apis: ['./src/routes/*.ts', './src/app.ts']
};

const swaggerSpec = swaggerJsdoc(options);

export function setupSwagger(app: Express) {
  // Swagger UI
  app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec, {
    customCss: '.swagger-ui .topbar { display: none }',
    customSiteTitle: 'ANE API Documentation'
  }));

  // JSON endpoint
  app.get('/api-docs.json', (req, res) => {
    res.setHeader('Content-Type', 'application/json');
    res.send(swaggerSpec);
  });
}

export default swaggerSpec;
