# Backend -> `/analyze_batch`: JSON y paralelizacion

Este documento resume como el backend construye el payload que envia al microservicio Python en `POST /analyze_batch`, y como divide el trabajo en paralelo.

Referencias principales:

- `backend/src/routes/reports.ts`
- `postprocesamiento/server_flask.py`

## Punto de entrada

El flujo ocurre dentro de:

- `POST /api/reports/compliance/:campaignId`

Implementacion:

- `backend/src/routes/reports.ts`

Ese endpoint:

1. Resuelve `campaignId`, `sensor_mac` y `umbral`.
2. Busca GPS del sensor o de la configuracion de la campaña.
3. Llama al servicio DANE `POST /localizar`.
4. Construye `dane` y `danes` con municipio central y adyacentes.
5. Lee todas las mediciones `sensor_data` de la campaña.
6. Convierte esas mediciones en frames para el microservicio Python.
7. Divide los frames en sub-batches.
8. Envia esos sub-batches en paralelo a `POST /analyze_batch`.

## JSON base que el backend arma por frame

Cada fila de `sensor_data` se transforma internamente en un objeto `frame` con esta forma:

```json
{
  "Pxx": [-92.1, -91.7, -90.2, -89.9],
  "start_freq_hz": 88000000,
  "end_freq_hz": 108000000,
  "timestamp": 1710000000000,
  "excursion": {
    "unit": "hz",
    "peak_to_peak_hz": 75000,
    "peak_deviation_hz": 225000,
    "rms_deviation_hz": 45000
  },
  "depth": {
    "unit": "percent",
    "peak_to_peak": 45,
    "peak_deviation": 95,
    "rms_deviation": 20
  }
}
```

Notas:

- `Pxx` sale de la columna `pxx`.
- `excursion` solo se agrega si existen columnas `excursion_*`.
- `depth` solo se agrega si existen columnas `depth_*`.
- `timestamp` se conserva por frame para que el resultado luego pueda mapearse a la medicion original.

## JSON que se envia a `/analyze_batch`

El backend no manda un solo frame. Manda un body con:

- `max_workers`
- `frames`

La forma real del request es:

```json
{
  "max_workers": 4,
  "frames": [
    {
      "frame": {
        "Pxx": [-92.1, -91.7, -90.2, -89.9],
        "start_freq_hz": 88000000,
        "end_freq_hz": 108000000,
        "timestamp": 1710000000000,
        "excursion": {
          "unit": "hz",
          "peak_to_peak_hz": 75000,
          "peak_deviation_hz": 225000,
          "rms_deviation_hz": 45000
        },
        "depth": {
          "unit": "percent",
          "peak_to_peak": 45,
          "peak_deviation": 95,
          "rms_deviation": 20
        }
      },
      "cumplimiento": 1,
      "dane": "11001",
      "danes": ["11001", "25754"],
      "picos": [],
      "umbral_db": 5,
      "delta_fc_khz": 100,
      "delta_bw_khz": 10
    }
  ]
}
```

## Significado de cada campo

### Campos de nivel superior

- `max_workers`: cantidad maxima de threads que el microservicio Python usara dentro de ese sub-batch.
- `frames`: lista de frames a procesar en una sola llamada HTTP.

### Campos por elemento de `frames`

- `frame`: medicion espectral completa.
- `cumplimiento`: siempre `1` en este flujo; obliga al motor Python a usar modo `compliance`.
- `dane`: codigo DANE central obtenido desde geolocalizacion.
- `danes`: lista de DANE central + adyacentes.
- `picos`: siempre `[]` en este flujo; no se usa modo `peaks`.
- `umbral_db`: umbral solicitado por frontend o default `5`.
- `delta_fc_khz`: tolerancia de frecuencia central tomada de `system_configurations`.
- `delta_bw_khz`: tolerancia de ancho de banda tomada de `system_configurations`.

## De donde sale cada valor

- `frame.Pxx`, `start_freq_hz`, `end_freq_hz`, `timestamp`, `excursion`, `depth`:
  salen de `sensor_data`.
- `cumplimiento`:
  el backend lo fija manualmente en `1`.
- `dane`:
  sale de `resultado.central.codigo_dane`.
- `danes`:
  se arma con el DANE central y `resultado.adyacentes[].codigo_dane`.
- `picos`:
  el backend lo fija en `[]`.
- `umbral_db`:
  sale de body/query del endpoint `/api/reports/compliance/:campaignId`; si no llega, usa `5`.
- `delta_fc_khz` y `delta_bw_khz`:
  salen de `system_configurations`; si no existen, usan `100` y `10`.

## Como paraleliza el backend

La paralelizacion ocurre en dos niveles.

### Nivel 1: sub-batches desde Node.js

El backend:

1. Parsea todos los frames validos de la campaña.
2. Calcula `GUNICORN_WORKERS = 4`.
3. Divide la lista total en `chunks`.
4. Construye un request `/analyze_batch` por cada chunk.
5. Hace `Promise.all(...)` para enviar todos esos requests en paralelo.

La idea es que cada sub-batch sea atendido por un worker distinto de gunicorn.

Ejemplo conceptual si hay 100 mediciones:

```json
{
  "total_frames": 100,
  "gunicorn_workers_asumidos": 4,
  "chunk_size_aprox": 25,
  "sub_batches": 4
}
```

Entonces no se hace un solo request de 100 frames. Se hacen 4 requests paralelos de unas 25 mediciones cada uno.

## Nivel 2: paralelizacion interna en Python

Cada request a `/analyze_batch` incluye:

```json
{
  "max_workers": 4
}
```

El endpoint Python:

1. Recibe `frames`.
2. Crea un `ThreadPoolExecutor(max_workers=max_workers)`.
3. Procesa cada frame del sub-batch con la misma logica de `/analyze`.
4. Devuelve `results` manteniendo el orden original.

O sea:

- Node paraleliza entre sub-batches.
- Python paraleliza dentro de cada sub-batch.

## Orden de resultados

Aunque los sub-batches y los frames se procesan en paralelo, el backend reconstituye el arreglo final en el mismo orden de las mediciones originales.

Esto es importante porque luego:

- toma `analysisResults.results`
- revisa `analysisResults.results_by_dane`
- y vuelve a unir cada salida con su `timestamp` y datos tecnicos originales.

## Ejemplo simplificado de paralelizacion

Supongamos 10 mediciones y 4 workers gunicorn:

```text
Frames originales: [0,1,2,3,4,5,6,7,8,9]

Chunk 1 -> [0,1,2]
Chunk 2 -> [3,4,5]
Chunk 3 -> [6,7,8]
Chunk 4 -> [9]
```

El backend manda 4 requests HTTP en paralelo:

```text
POST /analyze_batch  -> frames [0,1,2]
POST /analyze_batch  -> frames [3,4,5]
POST /analyze_batch  -> frames [6,7,8]
POST /analyze_batch  -> frames [9]
```

Cuando vuelven las respuestas, el backend las reordena otra vez a:

```text
[resultado0, resultado1, resultado2, resultado3, resultado4, ...]
```

## Lo que espera el endpoint Python

`/analyze_batch` espera exactamente:

```json
{
  "frames": [
    {
      "frame": {
        "Pxx": [...],
        "start_freq_hz": 0,
        "end_freq_hz": 0
      },
      "cumplimiento": 1,
      "dane": "11001",
      "danes": ["11001", "25754"],
      "picos": [],
      "umbral_db": 5,
      "delta_fc_khz": 100,
      "delta_bw_khz": 10
    }
  ],
  "max_workers": 4
}
```

Y responde:

```json
{
  "results": [
    {
      "mode": "compliance",
      "cumplimiento": 1,
      "results": [],
      "results_by_dane": {
        "11001": [],
        "25754": []
      }
    }
  ]
}
```

## Resumen operativo

- El backend siempre usa `/analyze_batch` para compliance real.
- Cada medicion de `sensor_data` se convierte en un item dentro de `frames`.
- Cada item lleva `frame + cumplimiento + dane + danes + umbral + tolerancias`.
- El backend divide las mediciones en sub-batches paralelos.
- Cada sub-batch se manda a un worker de gunicorn.
- Dentro de Python, cada sub-batch se vuelve a paralelizar con threads.
- Los resultados se reordenan al final para conservar correspondencia con las mediciones originales.
