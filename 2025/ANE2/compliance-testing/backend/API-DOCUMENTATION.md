# Documentación API ANE - Swagger

## Acceso a la Documentación

Una vez que el servidor backend está ejecutándose, puedes acceder a la documentación completa de la API en:

### Localmente
```
http://localhost:3000/api-docs
```

### Servidor de Producción (VPN)
```
http://172.23.90.25:3000/api-docs
```

### Servidor de Producción (Público)
```
http://rsm.ane.gov.co:3000/api-docs
```

## Estructura de la API

La documentación Swagger está organizada en las siguientes categorías:

### 1. **Sensor Data** (Endpoints para sensores físicos)
Endpoints POST que los sensores utilizan para enviar datos:
- `POST /api/sensor/status` - Enviar estado del sensor (batería, temperatura)
- `POST /api/sensor/gps` - Enviar ubicación GPS
- `POST /api/sensor/data` - Enviar datos de espectro radioeléctrico (FFT, potencias)
- `POST /api/sensor/audio` - Enviar audio demodulado (AM/FM)

**Ejemplo de uso desde un sensor:**
```bash
curl -X POST http://172.23.90.25:3000/api/sensor/data \
  -H "Content-Type: application/json" \
  -d '{
    "mac": "00:11:22:33:44:55",
    "Pxx": [-80.5, -82.3, -79.1, -81.2],
    "start_freq_hz": 88000000,
    "end_freq_hz": 108000000,
    "timestamp": 1702745000000,
    "lat": 4.711,
    "lng": -74.0721
  }'
```

### 2. **Sensor Query** (Consultas de datos)
Endpoints GET para consultar datos históricos:
- `GET /api/sensor/{mac}/latest-status` - Último estado
- `GET /api/sensor/{mac}/latest-gps` - Última ubicación GPS
- `GET /api/sensor/{mac}/latest-data` - Últimos datos de espectro
- `GET /api/sensor/{mac}/data/range` - Datos por rango de tiempo
- `GET /api/sensor/{mac}/configuration` - Configuración activa

### 3. **Sensor Control** (Control remoto de sensores)
Endpoints para configurar y controlar sensores:
- `POST /api/sensor/{mac}/configure` - Enviar configuración de escaneo
- `POST /api/sensor/{mac}/stop` - Detener adquisición
- `POST /api/sensor/{mac}/configuration` - Guardar configuración

**Ejemplo de configuración de sensor:**
```bash
curl -X POST http://172.23.90.25:3000/api/sensor/00:11:22:33:44:55/configure \
  -H "Content-Type: application/json" \
  -d '{
    "center_frequency": 98000000,
    "span": 20000000,
    "sample_rate_hz": 2400000,
    "resolution_hz": 10000,
    "antenna_port": 1,
    "window": "hann",
    "overlap": 0.5
  }'
```

### 4. **Sensors Management** (CRUD de sensores)
Gestión de dispositivos:
- `GET /api/sensors` - Listar todos los sensores
- `GET /api/sensors/{id}` - Obtener sensor por ID
- `GET /api/sensors/mac/{mac}` - Obtener sensor por MAC
- `POST /api/sensors` - Crear nuevo sensor
- `PUT /api/sensors/{id}` - Actualizar sensor
- `DELETE /api/sensors/{id}` - Eliminar sensor
- `GET /api/sensors/{id}/antennas` - Antenas del sensor
- `POST /api/sensors/{id}/antennas` - Asignar antena
- `DELETE /api/sensors/{sensorId}/antennas/{antennaId}` - Desasignar antena

### 5. **Antennas Management** (CRUD de antenas)
Gestión de antenas:
- `GET /api/antennas` - Listar todas las antenas
- `GET /api/antennas/{id}` - Obtener antena por ID
- `POST /api/antennas` - Crear nueva antena
- `PUT /api/antennas/{id}` - Actualizar antena
- `DELETE /api/antennas/{id}` - Eliminar antena

### 6. **Campaigns** (Campañas de medición)
Gestión de campañas programadas:
- `GET /api/campaigns` - Listar todas las campañas
- `GET /api/campaigns/{id}` - Obtener campaña específica
- `POST /api/campaigns` - Crear nueva campaña
- `PUT /api/campaigns/{id}` - Actualizar campaña
- `DELETE /api/campaigns/{id}` - Eliminar campaña
- `POST /api/campaigns/{id}/start` - Iniciar campaña
- `POST /api/campaigns/{id}/stop` - Detener campaña
- `GET /api/campaigns/{id}/data` - Obtener datos de la campaña

**Ejemplo de creación de campaña:**
```bash
curl -X POST http://172.23.90.25:3000/api/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Monitoreo FM Bogotá",
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "start_time": "08:00",
    "end_time": "18:00",
    "interval_seconds": 300,
    "start_freq_mhz": 88.0,
    "end_freq_mhz": 108.0,
    "bandwidth_mhz": 0.2,
    "resolution_khz": 10,
    "preset": "FM_BROADCAST",
    "sensors": ["00:11:22:33:44:55"]
  }'
```

### 7. **Reports** (Reportes)
Generación de reportes:
- `POST /api/reports/compliance/{campaignId}` - Generar reporte de cumplimiento normativo

### 8. **System** (Sistema)
Información general:
- `GET /` - Información de la API y endpoints disponibles

## Resolución de Problemas

### Error 404 al enviar datos desde un sensor

Si un sensor recibe error 404, verifica:

1. **URL correcta**: Asegúrate de usar el path completo con `/api/sensor/`
   ```
   Correcto:   http://172.23.90.25:3000/api/sensor/data
   Incorrecto: http://172.23.90.25:3000/sensor/data
   ```

2. **Método HTTP**: Verifica que estés usando el método correcto (POST para enviar datos, GET para consultar)

3. **Headers**: Asegúrate de incluir `Content-Type: application/json`

4. **Formato del body**: El JSON debe coincidir con el schema documentado en Swagger

### Validar endpoint específico

Usa la documentación Swagger para:
1. Ver el schema exacto requerido
2. Probar el endpoint directamente desde el navegador (botón "Try it out")
3. Ver ejemplos de requests y responses
4. Verificar los parámetros requeridos vs opcionales

## JSON Schema Validation

Todos los endpoints documentados en Swagger incluyen:
- **Schemas** completos de request/response
- **Ejemplos** funcionales
- **Descripciones** de cada campo
- **Validaciones** (required, tipos, formatos)

## Autenticación

Actualmente la API no requiere autenticación. Todos los endpoints son públicos.

## Rate Limiting

No hay límite de requests actualmente configurado.

## WebSocket

Además de la API REST, el sistema ofrece un WebSocket para datos en tiempo real:

```
ws://172.23.90.25:3000/ws
```

El WebSocket transmite:
- `sensor_status` - Estados de sensores
- `sensor_gps` - Actualizaciones de ubicación
- `sensor_data` - Datos de espectro en tiempo real
- `sensor_configure` - Comandos de configuración
- `sensor_stop` - Comandos de detención

## Exportar Documentación

### Obtener el spec en JSON
```bash
curl http://172.23.90.25:3000/api-docs.json > api-spec.json
```

### Importar en Postman
1. Abre Postman
2. Import → Link → `http://172.23.90.25:3000/api-docs.json`
3. Tendrás toda la colección de endpoints lista para probar

## Ejemplos de Integración

### Python (requests)
```python
import requests

# Enviar datos de espectro
data = {
    "mac": "00:11:22:33:44:55",
    "Pxx": [-80.5, -82.3, -79.1],
    "start_freq_hz": 88000000,
    "end_freq_hz": 108000000,
    "timestamp": 1702745000000
}

response = requests.post(
    "http://172.23.90.25:3000/api/sensor/data",
    json=data
)

print(response.json())
```

### JavaScript (fetch)
```javascript
// Consultar últimos datos de un sensor
fetch('http://172.23.90.25:3000/api/sensor/00:11:22:33:44:55/latest-data?limit=10')
  .then(res => res.json())
  .then(data => console.log(data))
  .catch(err => console.error(err));
```

### cURL
```bash
# Obtener todos los sensores
curl http://172.23.90.25:3000/api/sensors

# Enviar estado del sensor
curl -X POST http://172.23.90.25:3000/api/sensor/status \
  -H "Content-Type: application/json" \
  -d '{"mac":"00:11:22:33:44:55","battery":85.5,"temperature":28.5,"signal_quality":92.3,"timestamp":1702745000000}'
```

## Soporte

Para más información, consulta:
- Swagger UI: http://172.23.90.25:3000/api-docs
- Código fuente: `backend/src/routes/`
- Schema definitions: `backend/src/swagger.ts`
