# Postprocesamiento

Esta carpeta queda separada en dos capas:

- Operacion del servicio:
  - `server_flask.py`
  - `main.py`
  - `src/`
- Evaluacion y validacion offline:
  - `evaluation/`

## Flujo operativo actual

El contrato publico no cambio.

- `POST /analyze` sigue igual.
- `process_input(...)` sigue igual.
- La forma de entrada y salida del servidor sigue igual.
- El usuario hoy puede controlar solo los campos ya expuestos por el servidor y la CLI actual.

Los campos disponibles hoy para el usuario son:

- `frame`
- `cumplimiento`
- `picos`
- `corr`
- `lic`
- `dane`
- `danes`
- `municipio` legacy
- `umbral_db`

## Controles internos del detector

La logica nueva del detector simple usa controles internos como:

- `threshold_margin_db`
- `seed_prominence_db`
- `edge_prominence_db`
- `grow_threshold_relax_db`
- `min_prominence_db`
- `min_support_ratio`
- `min_bandwidth_hz`
- `max_gap_hz`
- `smooth_sigma_bins`
- `local_baseline_window_hz`
- `slow_rescue_*`

Hoy esos controles no estan expuestos en el flujo HTTP ni CLI publica.

## Estructura preparada para futura exposicion

Se dejo listo el contrato interno en:

- [user_controls.py](c:/Users/gilse/OneDrive/Escritorio/SDR/estimation_parameters_threshold/postprocesamiento/src/user_controls.py)

Ese modulo define:

- `DetectorUserControls`
- `resolve_simple_detector_controls(...)`
- `FUTURE_USER_CONTROL_FIELDS`

Con eso ya queda preparada la traduccion entre un payload futuro del usuario y los overrides internos del detector, sin tocar todavia el servidor.

## Evaluacion offline

Todo lo de benchmark, pruebas, reportes y utilidades manuales quedo en:

- `evaluation/`

La guia concreta esta en:

- `evaluation/README.md`
- `docs/CONTROL_USUARIO_Y_OPERACION.md`
