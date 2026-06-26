# ANE Backend

Backend para el sistema de monitoreo de señales de radio ANE.

## Características

- **REST API** para gestión de sensores y antenas
- **WebSocket** para datos en tiempo real
- **PostgreSQL** como base de datos
- **TypeScript** para type safety
- Recepción de datos desde sensores (status, GPS, spectrum data)
- Configuración de parámetros de medición

## Requisitos

- Node.js 18+
- npm o yarn

## Instalación

```bash
# Instalar dependencias
npm install

# Inicializar base de datos
npm run migrate
```

## Ejecución

### Desarrollo
```bash
npm run dev
```

### Producción
```bash
npm run build
npm start
```

El servidor estará disponible en:
- HTTP API: `http://localhost:3000`
- WebSocket: `ws://localhost:3000/ws`

## API Endpoints

### Gestión de Sensores

- `GET /api/sensors` - Listar todos los sensores
- `GET /api/sensors/:id` - Obtener sensor por ID
- `GET /api/sensors/mac/:mac` - Obtener sensor por MAC
- `POST /api/sensors` - Crear nuevo sensor
- `PUT /api/sensors/:id` - Actualizar sensor
- `DELETE /api/sensors/:id` - Eliminar sensor
- `GET /api/sensors/:id/antennas` - Obtener antenas del sensor
- `POST /api/sensors/:id/antennas` - Asignar antena a sensor
- `DELETE /api/sensors/:sensorId/antennas/:antennaId` - Desasignar antena

### Gestión de Antenas

- `GET /api/antennas` - Listar todas las antenas
- `GET /api/antennas/:id` - Obtener antena por ID
- `POST /api/antennas` - Crear nueva antena
- `PUT /api/antennas/:id` - Actualizar antena
- `DELETE /api/antennas/:id` - Eliminar antena

### Datos del Sensor (desde el hardware)

- `POST /api/sensor/status` - Recibir estado del sensor (CPU, RAM, etc.)
- `POST /api/sensor/gps` - Recibir ubicación GPS
- `POST /api/sensor/data` - Recibir datos de espectro
- `GET /api/sensor/:mac/latest-status` - Último estado del sensor
- `GET /api/sensor/:mac/latest-gps` - Última ubicación GPS
- `GET /api/sensor/:mac/latest-data?limit=100` - Últimos datos de espectro
- `GET /api/sensor/:mac/data/range?start=<ts>&end=<ts>` - Datos por rango de tiempo
- `POST /api/sensor/:mac/configuration` - Guardar configuración
- `GET /api/sensor/:mac/configuration` - Obtener configuración activa

## Estructura del Proyecto

```
backend/
├── src/
│   ├── app.ts                 # Servidor principal
│   ├── websocket.ts           # Configuración WebSocket
│   ├── types/
│   │   └── index.ts           # Interfaces TypeScript
│   ├── database/
│   │   ├── connection.ts      # Conexión PostgreSQL
│   │   └── migrate.ts         # Migraciones/esquemas
│   ├── models/
│   │   ├── Sensor.ts          # Modelo de Sensor
│   │   ├── Antenna.ts         # Modelo de Antena
│   │   └── SensorData.ts      # Modelo de datos del sensor
│   └── routes/
│       ├── management.ts      # Rutas de gestión
│       └── sensor.ts          # Rutas de datos del sensor
├── data/
│   └── ane.db                 # Base de datos (legacy)
├── package.json
└── tsconfig.json
```

## Ejemplos de Uso

### Crear un Sensor

```bash
curl -X POST http://localhost:3000/api/sensors \
  -H "Content-Type: application/json" \
  -d '{
    "mac": "00:11:22:33:44:55",
    "name": "Sensor Medellín",
    "description": "Sensor principal en Medellín",
    "lat": 6.2476,
    "lng": -75.5658,
    "status": "active"
  }'
```

### Crear una Antena

```bash
curl -X POST http://localhost:3000/api/antennas \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Antena FM-1",
    "type": "Dipolo",
    "frequency_min_hz": 88000000,
    "frequency_max_hz": 108000000,
    "gain_db": 3.5,
    "description": "Antena para banda FM"
  }'
```

### Enviar Datos de Espectro (desde el sensor)

```bash
curl -X POST http://localhost:3000/api/sensor/data \
  -H "Content-Type: application/json" \
  -d @../frontend/json/POST-data.json
```

### WebSocket (desde el frontend)

```javascript
const ws = new WebSocket('ws://localhost:3000/ws');

ws.onopen = () => {
  console.log('Connected to backend');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
  
  // Tipos de mensajes:
  // - sensor_status
  // - sensor_gps
  // - sensor_data (spectrum)
};
```

## Base de Datos

El sistema utiliza PostgreSQL con las siguientes tablas:

- `sensors` - Información de sensores
- `antennas` - Catálogo de antenas
- `sensor_antennas` - Relación sensor-antena
- `sensor_status` - Histórico de estado del sensor
- `sensor_gps` - Histórico de ubicaciones GPS
- `sensor_data` - Datos de espectro capturados
- `sensor_configurations` - Configuraciones de medición
- `campaigns` - Campañas de medición

## Variables de Entorno

Crear archivo `.env`:

```env
PORT=3000
DB_PATH=./data/ane.db
NODE_ENV=development
```

## Desarrollo

El backend está listo para recibir datos desde sensores físicos y enviarlos en tiempo real al frontend mediante WebSocket.

Los archivos JSON de ejemplo en `../frontend/json/` muestran el formato esperado para cada tipo de dato.
