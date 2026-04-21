# Python Postprocessing API

Documento de referencia del microservicio de postprocesamiento usado por el flujo de compliance. Sirve para depurar el contrato que consume el backend y para validar el servicio Python de forma aislada.

## Resumen

El servicio Python tiene dos formas principales de uso:

1. API HTTP con Flask, expuesta en `POST /analyze`
2. Ejecución por consola con `main.py` para probar el motor localmente

Además expone `GET /health` para verificación rápida.

## Estructura del servicio

Ruta base del servicio:

- [postprocesamiento.backup-20260420-165829/server_flask.py](postprocesamiento.backup-20260420-165829/server_flask.py)
- [postprocesamiento.backup-20260420-165829/main.py](postprocesamiento.backup-20260420-165829/main.py)

Componentes clave:

- [postprocesamiento.backup-20260420-165829/src/processor.py](postprocesamiento.backup-20260420-165829/src/processor.py)
- [postprocesamiento.backup-20260420-165829/src/payload_parser.py](postprocesamiento.backup-20260420-165829/src/payload_parser.py)
- [postprocesamiento.backup-20260420-165829/src/spectrum_frame.py](postprocesamiento.backup-20260420-165829/src/spectrum_frame.py)

## API HTTP

### `GET /health`

Respuesta simple de salud:

```json
{ "ok": true }
```

### `POST /analyze`

Endpoint principal para análisis espectral y cumplimiento.

El servidor se arranca por defecto en `http://127.0.0.1:8000` y el Dockerfile lo publica en el puerto `8000`.

## Formatos de entrada aceptados

### 1. Payload recomendado para compliance

El backend de compliance debe enviar un objeto JSON con esta forma:

```json
{
  "frame": {
    "Pxx": [
      -92.1,
      -91.7,
      -90.2
    ],
    "start_freq_hz": 88000000,
    "end_freq_hz": 108000000,
    "timestamp": 1710000000000
  },
  "cumplimiento": 1,
  "dane": "11001",
  "danes": ["11001", "17001"],
  "picos": [],
  "umbral_db": 5,
  "delta_fc_khz": 100,
  "delta_bw_khz": 10
}
```

Campos importantes:

- `frame.Pxx`: arreglo de potencias o amplitudes en dBm
- `frame.start_freq_hz` y `frame.end_freq_hz`: rango espectral
- `cumplimiento`: `1` para modo compliance, `0` para detección general
- `dane` o `danes`: filtro geográfico para la licencia
- `picos`: lista opcional de frecuencias objetivo
- `umbral_db`: umbral de detección sobre el piso de ruido
- `delta_fc_khz`: tolerancia de matching por frecuencia central
- `delta_bw_khz`: tolerancia de cumplimiento de ancho de banda

### 2. Payload crudo

También acepta el frame directo sin wrapper:

```json
{
  "Pxx": [-92.1, -91.7, -90.2],
  "start_freq_hz": 88000000,
  "end_freq_hz": 108000000
}
```

En ese modo, los metadatos se leen por query params.

### 3. JSON por archivo

Solo permitido si el servidor se levanta con `--allow-json-path`.

```json
{
  "json_path": "/ruta/al/frame.json",
  "cumplimiento": 1,
  "dane": "11001"
}
```

No se recomienda para producción.

## Reglas de parsing

El servidor detecta estos metadatos en el wrapper o en query params:

- `cumplimiento`
- `picos`
- `lic`
- `corr`
- `dane`
- `danes`
- `municipio`
- `umbral_db`
- `delta_fc_khz`
- `delta_bw_khz`

Reglas relevantes:

- Si llega `danes`, tiene prioridad sobre `dane`
- Si llega `municipio` numérico, se interpreta como DANE
- Si `cumplimiento = 0` y no hay `picos`, el motor ignora licencias y entra en modo detección general
- `umbral_db` se normaliza como flotante y puede ser `null` si no se envía

## Modos de operación

El motor interno selecciona un modo según `picos` y `cumplimiento`:

1. Si `picos` tiene elementos, usa modo `peaks`
2. Si no hay `picos` y `cumplimiento = 1`, usa modo `compliance`
3. Si no hay `picos` y `cumplimiento = 0`, usa modo `all_emissions`

## Uso desde el backend de compliance

El backend de reportes manda este payload al servicio Python:

```json
{
  "frame": { ... },
  "cumplimiento": 1,
  "dane": "codigo_dane",
  "danes": ["codigo_dane", "adyacentes"],
  "picos": [],
  "umbral_db": 5,
  "delta_fc_khz": 100,
  "delta_bw_khz": 10
}
```

Endpoint destino:

- `POST http://localhost:8000/analyze`

## Respuesta esperada

La respuesta exacta depende del modo, pero el servicio suele devolver campos como:

- `mode`
- `cumplimiento`
- `umbral_db`
- `picos_count`
- `num_emissions`
- `correction_applied`
- `timestamp`
- `mac`
- `results`
- `results_by_dane`

Para depuración, el servicio imprime un resumen y luego el contenido completo de `results` o `results_by_dane`.

## Entrada del parser de frame

El parser acepta los siguientes nombres de campos para el frame:

- `Pxx`, `pxx`, `PSD`, `psd`, `amplitudes_dbm`, `amplitudes`
- `start_freq_hz`, `f_start_hz`, `start_hz`, `f_start`, `start_freq`
- `end_freq_hz`, `f_stop_hz`, `stop_hz`, `f_stop`, `end_freq`, `stop_freq`

El `Pxx` debe tener al menos 4 puntos.

## Arranque local

### Servidor Flask

```bash
python server_flask.py --host 0.0.0.0 --port 8000
```

Opcionalmente puedes pasar CSV por defecto para licencias y correcciones:

```bash
python server_flask.py \
  --host 0.0.0.0 \
  --port 8000 \
  --lic-default /opt/ane-realtime/data/licencias.csv \
  --corr-default /ruta/correcciones.csv
```

### CLI de prueba

```bash
python main.py --json frame.json --cumplimiento 1 --dane 11001 --umbral_db 5
```

También acepta frame inline:

```bash
python main.py --frame '{"Pxx": [-92, -91, -90, -89], "start_freq_hz": 88000000, "end_freq_hz": 108000000}' --cumplimiento 0
```

## Docker

El contenedor arranca con:

```bash
python server_flask.py --host 0.0.0.0 --port 8000 --lic-default /opt/ane-realtime/data/licencias.csv
```

El `Dockerfile` también expone un healthcheck en:

- `GET http://localhost:8000/health`

## Archivos de prueba útiles

- [postprocesamiento.backup-20260420-165829/step1_test_payload.py](postprocesamiento.backup-20260420-165829/step1_test_payload.py)
- [postprocesamiento.backup-20260420-165829/step2_test_router.py](postprocesamiento.backup-20260420-165829/step2_test_router.py)
- [EXAMPLE_COMPLIANCE/api_requests_simple.py](EXAMPLE_COMPLIANCE/api_requests_simple.py)
- [EXAMPLE_COMPLIANCE/api_requests_varias_senales.py](EXAMPLE_COMPLIANCE/api_requests_varias_senales.py)

## Puntos donde suele romperse

1. El JSON no trae `frame.Pxx`, `frame.start_freq_hz` o `frame.end_freq_hz`
2. `Pxx` tiene muy pocos puntos
3. `dane` y `danes` llegan vacíos cuando se requiere validación por licencia
4. `umbral_db` llega inválido o no coincide con el esperado en backend
5. El backend manda un `frame` que no conserva el rango de frecuencia correcto
6. Se intenta usar `json_path` sin levantar el servidor con `--allow-json-path`

## Relación con compliance

El backend de reportes usa este microservicio como motor de análisis. Cuando se investiga un fallo de compliance, este documento sirve para verificar tres cosas:

1. Que el backend esté llamando al endpoint correcto
2. Que el payload tenga el frame y los metadatos esperados
3. Que el motor Python esté devolviendo resultados en el modo correcto