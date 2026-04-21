# Tutorial: hallar DANE en el backend API

## Resumen ejecutivo

En este backend no existe un endpoint público dedicado tipo `/api/geolocation` para “coordenadas -> DANE”.

La resolución DANE ocurre de dos maneras:

1. Consumo directo del servicio interno ANE `POST /localizar`.
2. Consumo indirecto dentro de `POST /api/reports/compliance/:campaignId`.

Referencias de código actual:

- `backend.backup-20260420-170013/src/routes/reports.ts`
- `backend.backup-20260420-170013/src/app.ts`

## Dónde se obtiene el DANE exactamente

En el flujo de compliance (`POST /api/reports/compliance/:campaignId`) el backend:

1. Resuelve coordenadas (`lat`, `lng`) de campaña/sensor.
2. Llama al servicio ANE: `POST http://172.23.80.220:4155/localizar` con `{ "lat": ..., "lon": ... }`.
3. Extrae `resultado.central.codigo_dane`.
4. Arma una lista `danes` con el DANE central y los adyacentes.
5. Envía `dane` y `danes` al microservicio Python `POST /analyze`.

## Opciones de uso disponibles

### Opcion A: consulta directa a geolocalizacion ANE

Endpoint interno:

- URL: `http://172.23.80.220:4155/localizar`
- Metodo: `POST`
- Headers usados por backend: `Content-Type: application/json`, `Accept: application/json`
- Body:

```json
{
  "lat": 4.711,
  "lon": -74.0721
}
```

Campos esperados de respuesta:

- `encontrado` (`boolean`)
- `resultado.central.departamento`
- `resultado.central.municipio`
- `resultado.central.codigo_dane`
- `resultado.adyacentes[]` (opcional)
- `resultado.radio_km` (opcional)

Ejemplo de respuesta:

```json
{
  "encontrado": true,
  "resultado": {
    "central": {
      "departamento": "Bogota D.C.",
      "municipio": "Bogota",
      "codigo_dane": "11001"
    },
    "radio_km": 0,
    "adyacentes": [
      {
        "departamento": "Cundinamarca",
        "municipio": "Soacha",
        "codigo_dane": "25754"
      }
    ]
  }
}
```

`curl`:

```bash
curl -X POST http://172.23.80.220:4155/localizar \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -d '{"lat":4.711,"lon":-74.0721}'
```

### Opcion B: usar endpoint de compliance (indirecto)

Endpoint backend:

- `POST /api/reports/compliance/:campaignId`

Este endpoint no recibe `lat/lon` directo. Obtiene coordenadas desde:

1. `campaign.config.gps.lat/lng` (prioridad alta)
2. `sensors.lat/lng`
3. `sensor_gps` (ultimo registro)

Si no encuentra GPS, devuelve `404`.

## Todas las opciones de entrada de compliance

### Path params

- `campaignId` (requerido)

### Query params

- `sensor_mac` (opcional): fuerza el sensor a usar y valida pertenencia a la campana.
- `force=true` (opcional): evita usar cache y fuerza regeneracion.
- `umbral` (opcional): umbral de deteccion en dB.
- `umbral_db` (opcional): alias de `umbral`.

### Body params

- `umbral` (opcional)
- `umbral_db` (opcional)

Precedencia para umbral:

1. `body.umbral`
2. `query.umbral`
3. `body.umbral_db`
4. `query.umbral_db`
5. default `5`

Regla de normalizacion:

- Si el umbral es invalido o negativo, se ajusta a `0`.

## Comportamiento DANE en compliance

Cuando geolocalizacion responde correctamente:

1. Toma `codigo_dane` central.
2. Agrega adyacentes (`resultado.adyacentes[].codigo_dane`) sin duplicados.
3. Envia al Python:

```json
{
  "cumplimiento": 1,
  "dane": "11001",
  "danes": ["11001", "25754"],
  "umbral_db": 5,
  "delta_fc_khz": 100,
  "delta_bw_khz": 10
}
```

Si el servicio Python devuelve `results_by_dane`, el backend reevalua emisiones para intentar autorizar por municipios adyacentes.

## Errores y respuestas relevantes

### Errores de geolocalizacion/DANE

- `503 Geolocation service unavailable`: no pudo conectar con `172.23.80.220:4155`.
- `404 Location not found`: coordenadas fuera del territorio nacional o sin match.
- `400 DANE code not available`: geolocalizacion sin `codigo_dane` usable.

### Errores de datos de campana/sensor

- `404 Campaign not found`
- `400 Campaign has no sensors assigned`
- `400 Sensor not assigned to this campaign`
- `404 No GPS data found for sensor (manual or automatic)`
- `404 No spectrum data found for campaign`

## Ejemplos de uso

### 1) Solo obtener DANE por coordenadas

```bash
curl -X POST http://172.23.80.220:4155/localizar \
  -H 'Content-Type: application/json' \
  -d '{"lat":4.711,"lon":-74.0721}'
```

### 2) Generar compliance con sensor explicito y umbral

```bash
curl -X POST "http://localhost:3000/api/reports/compliance/123?sensor_mac=AA:BB:CC:DD:EE:FF&umbral=6" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 3) Forzar regeneracion ignorando cache

```bash
curl -X POST "http://localhost:3000/api/reports/compliance/123?force=true" \
  -H "Content-Type: application/json" \
  -d '{"umbral_db":5}'
```

## Notas operativas

- El cache de compliance solo aplica cuando: `umbral=5`, sin `sensor_mac`, y `force` distinto de `true`.
- En este snapshot no se observa auth en la llamada interna a `/localizar`.
- Si no hay conectividad de red al servicio interno, usar tunel SSH o exponer un proxy controlado.

## Referencias relacionadas

- `COMPLIANCE_API_FLOW.md`
- `PYTHON_POSTPROCESSING_API.md`
- `backend.backup-20260420-170013/src/routes/reports.ts`
