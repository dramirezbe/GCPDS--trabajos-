# Ejemplo de uso de la API de `postprocesamiento`

Estos ejemplos usan `requests` de Python contra `localhost`, sin Docker.

## 1. Levantar el servidor

Desde la raíz del repo:

```bash
python3 postprocesamiento/server_flask.py --host 127.0.0.1 --port 8000
```

Health check opcional:

```bash
curl http://127.0.0.1:8000/health
```

## 2. Requisitos para los ejemplos

Si no tienes las dependencias instaladas:

```bash
pip install -r postprocesamiento/requirements.txt requests
```

## 3. Generar espectros sintéticos con ruido gaussiano

Los scripts quedaron en `examples/`.

Para generar los JSON de ejemplo:

```bash
python3 examples/synthetic_frames.py --kind both
```

Eso crea:

- `examples/generated/frame_ruido_gaussiano_single.json`
- `examples/generated/frame_ruido_gaussiano_multi.json`

El formato generado es compatible con la API porque incluye:

- `Pxx`
- `start_freq_hz`
- `end_freq_hz`

## 4. Ejemplo simple con `requests`

Este ejemplo genera un frame con ruido gaussiano y una señal sintética, lo guarda en disco y lo envía a `/analyze`.

```bash
python3 examples/api_requests_simple.py
```

Payload enviado:

```json
{
  "frame": {
    "Pxx": [...],
    "start_freq_hz": 88000000.0,
    "end_freq_hz": 108000000.0
  },
  "cumplimiento": 0,
  "umbral_db": 6
}
```

## 5. Ejemplo de reporte de varias señales

Sí existe esta funcionalidad.

Si envías `cumplimiento=0` y no mandas `picos`, la API entra en modo `all_emissions` y devuelve un reporte con todas las emisiones detectadas en el frame.

Ejemplo:

```bash
python3 examples/api_requests_varias_senales.py
```

Ese script genera un espectro con varias señales sobre ruido gaussiano y espera una respuesta con campos como:

- `mode`
- `num_emissions`
- `results`

## 6. Estructura mínima del request

La forma recomendada para consumir la API es:

```python
import requests

payload = {
    "frame": {
        "Pxx": [-98.1, -97.8, -98.4],
        "start_freq_hz": 88e6,
        "end_freq_hz": 108e6,
    },
    "cumplimiento": 0,
}

resp = requests.post("http://127.0.0.1:8000/analyze", json=payload, timeout=60)
print(resp.json())
```

## 7. Nota sobre reportes por varios DANE

La API también soporta `danes` en el request, por ejemplo:

```json
{
  "frame": { "...": "..." },
  "cumplimiento": 1,
  "lic": "ruta/al/csv.csv",
  "danes": ["11001", "17001"]
}
```

En ese caso puede devolver `results_by_dane`.
