# Control De Usuario Y Operacion

## Estado actual

La plataforma hoy conserva el flujo historico del servidor.

El usuario no controla directamente los parametros finos del detector simple.
Eso fue intencional: primero se optimizo la logica interna y se mantuvo intacto el contrato externo.

## Lo que el usuario si controla hoy

Via servidor o CLI actual:

- `frame`
- `cumplimiento`
- `picos`
- `corr`
- `lic`
- `dane`
- `danes`
- `municipio` legacy
- `umbral_db`

## Lo que aun no controla el usuario

Los parametros internos de la deteccion:

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
- `slow_rescue_window_scale`
- `slow_rescue_delta_db`
- `slow_rescue_peak_prominence_db`
- `slow_rescue_max_width_factor`
- `slow_rescue_gap_hz`
- `slow_rescue_max_existing_segments`

## Donde quedo preparada la futura integracion

La base para exponer esos controles ya esta lista en:

- [user_controls.py](c:/Users/gilse/OneDrive/Escritorio/SDR/estimation_parameters_threshold/postprocesamiento/src/user_controls.py)

El modulo ya define:

- un contrato tipado para controles futuros;
- un mapeo estable a overrides del detector simple;
- una tabla de campos soportados.

## Como deberia hacerse despues

Cuando se quiera exponer control al usuario, el cambio recomendado es:

1. Aceptar un bloque opcional de controles en `server_flask.py` y/o `main.py`.
2. Convertir ese bloque con `resolve_simple_detector_controls(...)`.
3. Pasar el preset y los overrides resultantes a `get_detector_run(...)`.
4. Mantener defaults actuales cuando el bloque no venga presente.

## Lo que no se toco

- Contrato de `POST /analyze`
- `process_input(...)`
- formatos actuales de entrada y salida
- forma de conexion con el servidor

## Configuracion operativa recomendada hoy

La mejor configuracion interna validada hasta ahora ya queda embebida en:

- [simple_detector.py](c:/Users/gilse/OneDrive/Escritorio/SDR/estimation_parameters_threshold/postprocesamiento/src/simple_detector.py)
- [benchmark_tes_signals.py](c:/Users/gilse/OneDrive/Escritorio/SDR/estimation_parameters_threshold/postprocesamiento/evaluation/benchmark_tes_signals.py)

Esa es la configuracion que usa la evaluacion offline actual y la referencia interna del detector simple.
