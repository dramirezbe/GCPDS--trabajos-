# Compliance API Flow

Referencia rápida del flujo de generación de reporte de cumplimiento normativo. Este documento se usa como base para depurar el servicio de Python y el backend cuando algo falla en el reporte.

## Ruta principal

- Frontend llama a `POST /api/reports/compliance/:campaignId`
- Backend resuelve campaña, sensor, GPS y geolocalización
- Backend construye el payload y llama al servicio Python en `POST /analyze`
- El servicio Python retorna el análisis de emisiones y cumplimiento
- Backend reformatea la respuesta y la devuelve al frontend

## Enfoque DANE en este flujo

Este endpoint es la via indirecta para resolver DANE dentro del backend.

Pasos clave de DANE:

1. Determina coordenadas (`lat`, `lng`) desde campaña/sensor.
2. Llama `POST http://172.23.80.220:4155/localizar` con `{ lat, lon }`.
3. Toma `resultado.central.codigo_dane` como DANE principal.
4. Agrega `resultado.adyacentes[].codigo_dane` para construir `danes`.
5. Envia `dane` y `danes` al microservicio Python `POST /analyze`.

Si falla la geolocalización, no hay análisis de cumplimiento.

## Frontend que dispara el flujo

Los componentes que invocan el reporte de compliance son:

- [src/components/CampaignDataViewer.tsx](frontend.backup-20260419-085444/src/components/CampaignDataViewer.tsx)
- [src/components/ComplianceReport.tsx](frontend.backup-20260419-085444/src/components/ComplianceReport.tsx)
- [src/components/AlertsPanel.tsx](frontend.backup-20260419-085444/src/components/AlertsPanel.tsx)

La URL base del frontend para la API es:

- En local: `http://localhost:3000/api` por defecto, o `VITE_API_URL` si está definido
- En producción: `/api`

## Endpoint del backend

El router de reportes está montado en:

- [src/app.ts](backend.backup-20260420-170013/src/app.ts)

Endpoint expuesto:

- `POST /api/reports/compliance/:campaignId`
- `POST /api/reports/compliance/batch/:campaignId` (lista sensores para ejecutar reportes individuales)

Implementación principal:

- [src/routes/reports.ts](backend.backup-20260420-170013/src/routes/reports.ts)

## Parametros y opciones (compliance)

### Path params

- `campaignId` (requerido)

### Query params

- `sensor_mac` (opcional): usa un sensor concreto y valida que pertenezca a la campaña.
- `force` (opcional): si `true`, desactiva cache y fuerza regeneración.
- `umbral` (opcional): umbral en dB.
- `umbral_db` (opcional): alias de `umbral`.

### Body

- `umbral` (opcional)
- `umbral_db` (opcional)

## Manejo de `umbral`

El backend acepta `umbral` de estas formas:

- `req.body.umbral`
- `req.query.umbral`
- `req.body.umbral_db`
- `req.query.umbral_db`

Regla de negocio actual:

- Si llega `umbral`, se parsea como número y se usa como `UMBRAL_DB`
- Si no llega ningún valor, el backend usa `UMBRAL_DB = 5`
- Si el valor es inválido o negativo, se normaliza a `0`

Precedencia exacta implementada:

1. `body.umbral`
2. `query.umbral`
3. `body.umbral_db`
4. `query.umbral_db`
5. default `5`

## Cuándo usa caché

El backend puede responder desde caché cuando se cumplen estas condiciones:

- `force` no es `true`
- `UMBRAL_DB === 5`
- no se envía `sensor_mac`

Si se envía `sensor_mac`, el caché queda deshabilitado para esa solicitud.

## Resolución de sensor y GPS

Orden de decisión:

1. Si llega `sensor_mac`, se valida que pertenezca a la campaña
2. Si no llega `sensor_mac`, se toma el primer sensor asociado a la campaña
3. Se busca GPS manual en la configuración de la campaña
4. Si no existe, se busca lat/lng en tabla `sensors`
5. Si no existe, se busca historial en `sensor_gps`
6. Si no hay GPS, el backend responde `404`

## Resolución DANE y adyacentes

Luego de resolver GPS:

1. Backend llama al servicio ANE de geolocalización.
2. Valida que `encontrado=true` y exista `resultado.central`.
3. Exige `codigo_dane` central para continuar.
4. Construye `danes` con:
   - DANE central
   - DANE(s) adyacente(s) si existen
5. Envia ambos campos al Python:

```json
{
  "dane": "11001",
  "danes": ["11001", "25754"]
}
```

Si Python responde `results_by_dane`, el backend revisa emisiones sin licencia para intentar autorizarlas por adyacentes.

## Llamado al servicio Python

El backend construye un payload y llama a:

- `POST ${PYTHON_SERVICE_URL}/analyze`
- `PYTHON_SERVICE_URL` por defecto: `http://localhost:8000`

Payload principal enviado al servicio Python:

```json
{
  "frame": {
    "Pxx": [],
    "start_freq_hz": 0,
    "end_freq_hz": 0,
    "timestamp": 0,
    "excursion": {},
    "depth": {}
  },
  "cumplimiento": 1,
  "dane": "codigo_dane",
  "danes": ["codigo_dane", "adyacentes..."],
  "picos": [],
  "umbral_db": 5,
  "delta_fc_khz": 0,
  "delta_bw_khz": 0
}
```

Notas de opciones relevantes en payload:

- `cumplimiento` se fija en `1`.
- `picos` se manda como `[]` en este flujo.
- `delta_fc_khz` y `delta_bw_khz` se leen de `system_configurations` con defaults `100` y `10`.

## Qué devuelve el backend

El backend transforma la respuesta de Python en un formato con:

- `measurement`
- `stats`
- `emisiones`
- clasificación de cada emisión como `CUMPLE`, `FUERA_PARAMETROS` o `SIN_LICENCIA`

Campos de ubicación relevantes en respuesta final:

- `ubicacion.departamento`
- `ubicacion.municipio`
- `ubicacion.codigo_dane`
- `ubicacion.coordenadas.latitud`
- `ubicacion.coordenadas.longitud`

## Puntos de falla a revisar primero

Cuando el reporte de compliance falla, revisar en este orden:

1. `POST /api/reports/compliance/:campaignId` llega con `campaignId` válido
2. `sensor_mac` existe y pertenece a la campaña, si fue enviado
3. La campaña tiene GPS manual o el sensor tiene lat/lng
4. El servicio ANE de geolocalización responde correctamente
5. `PYTHON_SERVICE_URL` apunta al servicio correcto
6. El endpoint `POST /analyze` del servicio Python está disponible
7. El payload contiene `umbral_db` con el valor esperado

Errores HTTP comunes del endpoint:

- `404 Campaign not found`
- `400 Campaign has no sensors assigned`
- `400 Sensor not assigned to this campaign`
- `404 No GPS data found for sensor (manual or automatic)`
- `503 Geolocation service unavailable`
- `404 Location not found`
- `400 DANE code not available`
- `404 No spectrum data found for campaign`
- `500 Failed to generate report`

## Casos de prueba rápidos

### Con umbral explícito

```bash
curl -X POST "http://localhost:3000/api/reports/compliance/123?sensor_mac=AA:BB:CC:DD:EE:FF" \
  -H "Content-Type: application/json" \
  -d '{"umbral": 5}'
```

### Sin umbral

```bash
curl -X POST "http://localhost:3000/api/reports/compliance/123?sensor_mac=AA:BB:CC:DD:EE:FF" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Forzar regeneración sin caché

```bash
curl -X POST "http://localhost:3000/api/reports/compliance/123?force=true" \
  -H "Content-Type: application/json" \
  -d '{"umbral_db": 5}'
```

### Listar sensores para ejecución por lote

```bash
curl -X POST "http://localhost:3000/api/reports/compliance/batch/123"
```

Ambos casos terminan enviando `umbral_db: 5` al servicio Python si no se especifica otro valor.