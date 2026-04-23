# Backend -> `/analyze`: JSON esperado y significado

Este documento explica como se ve el payload de `POST /analyze` desde la perspectiva del backend.

Aunque el flujo actual de compliance real usa `POST /analyze_batch`, cada elemento dentro de `frames[]` sigue exactamente la misma logica y estructura base que `/analyze`.

En otras palabras:

- `/analyze` procesa 1 frame
- `/analyze_batch` procesa N frames
- cada frame de `/analyze_batch` equivale a un request individual a `/analyze`

Referencias principales:

- `backend/src/routes/reports.ts`
- `postprocesamiento/server_flask.py`
- `postprocesamiento/src/payload_parser.py`
- `postprocesamiento/src/processor.py`

## Que espera `/analyze`

El endpoint espera una medicion espectral mas metadatos de analisis.

La forma recomendada es un wrapper JSON con:

- `frame`
- `cumplimiento`
- `dane` o `danes`
- `picos`
- `umbral_db`
- `delta_fc_khz`
- `delta_bw_khz`

## JSON recomendado

```json
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
```

## Forma minima valida

Lo minimo obligatorio dentro de `frame` es:

```json
{
  "frame": {
    "Pxx": [-92.1, -91.7, -90.2, -89.9],
    "start_freq_hz": 88000000,
    "end_freq_hz": 108000000
  },
  "cumplimiento": 1
}
```

## Campos obligatorios reales

Para que el parser construya el `SpectrumFrame`, necesita:

- `Pxx`
- `start_freq_hz`
- `end_freq_hz`

Ademas:

- `Pxx` debe tener al menos 4 puntos

## Alias aceptados en `frame`

El parser tolera varios nombres alternativos.

### Para amplitudes

- `Pxx`
- `pxx`
- `PSD`
- `psd`
- `amplitudes_dbm`
- `amplitudes`

### Para frecuencia inicial

- `start_freq_hz`
- `f_start_hz`
- `start_hz`
- `f_start`
- `start_freq`

### Para frecuencia final

- `end_freq_hz`
- `f_stop_hz`
- `stop_hz`
- `f_stop`
- `end_freq`
- `stop_freq`

## Significado de cada campo

### `frame`

Es la medicion espectral base sobre la que se corre todo el analisis.

Contiene:

- `Pxx`: vector espectral
- `start_freq_hz`: frecuencia inicial
- `end_freq_hz`: frecuencia final
- `timestamp`: opcional, pero el backend suele enviarlo
- `excursion`: opcional, usado para FM
- `depth`: opcional, usado para AM

### `cumplimiento`

Controla el modo de operacion del motor.

- `1`: modo `compliance`
- `0`: si no hay `picos`, entra en `all_emissions`

### `dane`

Codigo DANE principal. Es el filtro geografico clasico para licencias.

### `danes`

Lista de DANE central y municipios adyacentes.

Si llega `danes`, tiene prioridad sobre `dane`.

### `picos`

Lista de frecuencias objetivo.

Si tiene elementos, el modo pasa a `peaks` incluso si `cumplimiento=1`.

### `umbral_db`

Umbral relativo en dB sobre el piso de ruido.

No es el umbral absoluto final en dBm; el motor internamente calcula el umbral absoluto real a partir del ruido estimado.

### `delta_fc_khz`

Tolerancia de matching para frecuencia central.

### `delta_bw_khz`

Tolerancia de cumplimiento para ancho de banda.

## Como lo interpreta internamente

`/analyze` no analiza el JSON directamente en bruto. Primero lo transforma a:

```python
[frame_json, picos_list, cumplimiento]
```

Y luego llama a:

```python
process_input(
    payload,
    corr_csv_path=...,
    licencia_csv_path=...,
    dane_filtro=...,
    danes_filtro=...,
    municipio_filtro=...,
    umbral_db=...,
    delta_fc_khz=...,
    delta_bw_khz=...
)
```

## Modos internos que puede activar

El motor decide el modo asi:

1. Si `picos` tiene elementos -> `peaks`
2. Si no hay `picos` y `cumplimiento == 1` -> `compliance`
3. Si no hay `picos` y `cumplimiento == 0` -> `all_emissions`

## Que manda el backend en el flujo de compliance

En el flujo real del backend, por cada medicion se arma este tipo de payload unitario:

```json
{
  "frame": {
    "Pxx": [...],
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
```

La diferencia es que hoy ese payload no se envia solo a `/analyze`, sino embebido dentro de `frames[]` hacia `/analyze_batch`.

## Que no usa el backend normalmente

Aunque `/analyze` soporta otras variantes, el backend de compliance no suele usar:

- `json_path`
- `municipio` como filtro legacy
- `picos` con valores
- `cumplimiento = 0`
- query params para metadatos

El backend usa siempre el wrapper JSON estructurado.

## Reglas importantes

### Si `cumplimiento = 0` y `picos = []`

El servidor desactiva el uso de licencias y entra en deteccion general.

### Si llega `danes`

El motor puede devolver:

```json
{
  "results_by_dane": {
    "11001": [...],
    "25754": [...]
  }
}
```

Ademas mantiene compatibilidad dejando `results` con el primer DANE.

### Si el modo es `compliance`

Debe existir acceso al CSV de licencias, sea por:

- `lic` en el request
- o `ANE_LIC_CSV`/default configurado en el servidor

## Resumen corto

- `/analyze` espera un solo frame mas metadatos.
- El corazon del payload es `frame.Pxx + start_freq_hz + end_freq_hz`.
- Para compliance, el backend manda `cumplimiento=1`, `dane`, `danes`, `picos=[]`, `umbral_db` y tolerancias.
- Internamente eso se transforma y termina en `process_input(...)`.
- El flujo batch actual es simplemente la version vectorizada de este mismo contrato.
