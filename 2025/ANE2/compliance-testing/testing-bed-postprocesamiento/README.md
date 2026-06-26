# Flujo de Prueba de Cumplimiento

Este repositorio contiene un flujo de prueba para procesar una campaña de mediciones, enviarla a la API local de cumplimiento y visualizar los resultados.

La idea es que otra IA o cualquier desarrollador pueda reproducir el flujo completo cambiando solo el número de campaña.

## Resumen del flujo

1. Levantar la API local de cumplimiento con `./run_server_flask.sh`.
2. Ejecutar `EXAMPLE_COMPLIANCE/campaign_danes_API_cumpli.py` para:
   - descargar la campaña desde la API remota de ANE,
   - resolver los códigos DANE por túnel SSH,
   - generar payloads por señal,
   - enviar cada payload a `http://127.0.0.1:8000/analyze`,
   - guardar las respuestas JSON.
3. Ejecutar `EXAMPLE_COMPLIANCE/plot_response_API_cumpli.py` para visualizar las respuestas sobre la Pxx original.

## Estructura relevante

- `run_server_flask.sh`
  Arranca el servidor Flask local en `127.0.0.1:8000` usando el `venv` del proyecto.

- `postprocesamiento/server_flask.py`
  Implementa el endpoint `/analyze`.

- `EXAMPLE_COMPLIANCE/campaign_danes_API_cumpli.py`
  Ejecuta el flujo de cumplimiento para una campaña y guarda:
  - `EXAMPLE_COMPLIANCE/camp-<N>-signals`
  - `EXAMPLE_COMPLIANCE/camp-<N>-responses`

- `EXAMPLE_COMPLIANCE/plot_response_API_cumpli.py`
  Lee esas carpetas y muestra los plots uno por uno.

- `EXAMPLE_COMPLIANCE/modules/danes_request.py`
  Cliente de consulta DANE vía túnel SSH.

- `map_geolocal_danes.py`
  Genera un mapa HTML interactivo con filtros por coordenadas, frecuencia y radio a partir del consolidado de licencias DANE.

## Prerrequisitos

- Ejecutar los comandos desde la raíz de este repositorio.
- Tener disponible el `venv` local que usa `run_server_flask.sh`.
- Tener acceso a la red/servicios remotos de ANE si se va a ejecutar el flujo completo.
- Mantener el servidor Flask corriendo mientras se ejecuta `campaign_danes_API_cumpli.py`.

## Comandos para cualquier campaña

Sustituye `<N>` por el número de campaña que quieras probar.

Terminal 1:

```bash
./run_server_flask.sh
```

Terminal 2:

```bash
py EXAMPLE_COMPLIANCE/campaign_danes_API_cumpli.py -n <N>
```

Terminal 3:

```bash
py EXAMPLE_COMPLIANCE/plot_response_API_cumpli.py -n <N>
```

Si `py` no existe en tu entorno, usa `python` en su lugar:

```bash
python EXAMPLE_COMPLIANCE/campaign_danes_API_cumpli.py -n <N>
python EXAMPLE_COMPLIANCE/plot_response_API_cumpli.py -n <N>
```

## Ejemplo completo para la campaña 285

Terminal 1:

```bash
./run_server_flask.sh
```

Terminal 2:

```bash
py EXAMPLE_COMPLIANCE/campaign_danes_API_cumpli.py -n 285
```

Terminal 3:

```bash
py EXAMPLE_COMPLIANCE/plot_response_API_cumpli.py -n 285
```

## Salidas esperadas

Al ejecutar la campaña `<N>`, el script genera por defecto:

- `EXAMPLE_COMPLIANCE/camp-<N>-signals`
  Contiene un JSON por señal listo para enviar al endpoint `/analyze`.

- `EXAMPLE_COMPLIANCE/camp-<N>-responses`
  Contiene un JSON de respuesta por cada señal procesada.

Luego `plot_response_API_cumpli.py` toma ambos directorios y:

- carga la Pxx original,
- superpone emisiones medidas y anchos de banda,
- muestra información de licencia y checks de cumplimiento,
- abre una ventana por cada respuesta, en secuencia.

## Parámetros útiles

### `campaign_danes_API_cumpli.py`

- `-n <N>`
  Número de campaña.

- `--signals-folder <ruta>`
  Sobrescribe la carpeta de salida de señales.

- `--responses-folder <ruta>`
  Sobrescribe la carpeta de salida de respuestas.

### `plot_response_API_cumpli.py`

- `-n <N>`
  Número de campaña.

- `--signals-dir <ruta>`
  Usa una carpeta manual de señales.

- `--responses-dir <ruta>`
  Usa una carpeta manual de respuestas.

- `--pattern <texto>`
  Filtra archivos por nombre.

- `--start-index <i>`
  Empieza a mostrar desde cierto índice.

- `--limit <k>`
  Limita la cantidad de plots.

- `--no-show`
  Construye los plots sin abrir ventanas. Sirve para validación rápida.

### `map_geolocal_danes.py`

Script utilitario para explorar geográficamente las licencias del CSV
`postprocesamiento/consolidado_bbdd_asignación.csv`.

Genera un HTML interactivo (`int_map_danes.html` por defecto) con:

- centro de búsqueda configurable por latitud/longitud,
- filtro por rango de frecuencia en MHz,
- filtro por radio en kilómetros,
- puntos coloreados por frecuencia,
- popup con `codigo_dane`, frecuencia, distancia, distintivo, estado y servicio,
- controles dentro de la misma página para reajustar los filtros sin regenerar el archivo.

Ejemplo con los valores por defecto del script:

```bash
python3 map_geolocal_danes.py
```

Ejemplo indicando centro, rango de frecuencia y radio:

```bash
python3 map_geolocal_danes.py 4.6775 -74.0541 484.9 485.1 30
```

Ejemplo generando el HTML sin abrir navegador:

```bash
python3 map_geolocal_danes.py --no-open
```

Ejemplo usando otro CSV y otro archivo de salida:

```bash
python3 map_geolocal_danes.py --csv /ruta/licencias.csv --output /tmp/mapa_dane.html
```

Parámetros útiles:

- `lat`
  Latitud central. Por defecto: `4.6775`.

- `lon`
  Longitud central. Por defecto: `-74.0541`.

- `freq_inf_mhz`
  Frecuencia inferior. Por defecto: `484.9`.

- `freq_sup_mhz`
  Frecuencia superior. Por defecto: `485.1`.

- `km`
  Radio de búsqueda en kilómetros. Por defecto: `30`.

- `--csv <ruta>`
  CSV fuente. Por defecto: `postprocesamiento/consolidado_bbdd_asignación.csv`.

- `--output, -o <ruta>`
  HTML de salida. Por defecto: `int_map_danes.html`.

- `--max-rendered <N>`
  Limita cuántos puntos se dibujan al tiempo para no sobrecargar el navegador. Por defecto: `3000`.

- `--no-open`
  Solo genera el HTML y no intenta abrirlo.

- `--open-mode server`
  Sirve el HTML por `localhost` antes de abrirlo. Es el modo por defecto y evita problemas de tiles con `file://`.

- `--open-mode file`
  Abre directamente el HTML como archivo local.

- `--host <host>`
  Host del servidor local si se usa `--open-mode server`. Por defecto: `127.0.0.1`.

- `--port <puerto>`
  Puerto del servidor local si se usa `--open-mode server`. Usa `0` para seleccionar uno libre automáticamente.

## Notas operativas

- `campaign_danes_API_cumpli.py` actualmente usa coordenadas fijas de Bogotá (`lat=4.6775`, `lon=-74.0541`) para resolver los códigos DANE antes de procesar la campaña.
- El endpoint local esperado por el script es `http://127.0.0.1:8000/analyze`.
- Si el servidor no está arriba, la fase de envío a la API va a fallar.
- Si falla el túnel SSH o el acceso a ANE, no se podrán resolver los códigos DANE ni descargar datos remotos.

## Checklist rápido de debugging

- Verifica que `./run_server_flask.sh` siga corriendo.
- Verifica que exista `venv/` o `.venv/` en la raíz del repo.
- Verifica que `postprocesamiento/consolidado_bbdd_asignación.csv` exista.
- Verifica conectividad hacia los servicios remotos de ANE.
- Verifica que se hayan creado las carpetas `camp-<N>-signals` y `camp-<N>-responses` dentro de `EXAMPLE_COMPLIANCE`.
