# Salida JSON de `/analyze` usada por el backend

Este documento explica solo la salida que le importa al backend de compliance.

No cubre otros modos. Solo cubre el caso real que usa el backend:

- `cumplimiento = 1`
- `picos = []`
- modo interno `compliance`
- posible uso de `danes` y `results_by_dane`

Referencias:

- `postprocesamiento/src/processor.py`
- `backend/src/routes/reports.ts`
- `EXAMPLE_COMPLIANCE/responses_jeisson_api_compliance/`

## Forma general de la respuesta

La salida relevante para el backend se ve asi:

```json
{
  "correction_applied": false,
  "cumplimiento": 1,
  "mode": "compliance",
  "num_emissions": 1,
  "picos": [],
  "picos_count": 0,
  "umbral_db": 5.0,
  "umbral": -91.27,
  "danes": ["11001", "25754"],
  "results": [
    {
      "fc_medida_MHz": 479.0,
      "fc_nominal_MHz": null,
      "delta_f_MHz": null,
      "bw_medido_kHz": 5810.479594389737,
      "bw_nominal_kHz": null,
      "delta_bw_kHz": null,
      "p_medida_dBm": -48.952380054447644,
      "p_nominal_dBm": null,
      "delta_p_dB": null,
      "Cumple_FC": null,
      "Cumple_BW": null,
      "Cumple_P": null,
      "Licencia": "NO",
      "mer_db": 3.4100500428919376,
      "ber_est": 0.12501813547159088,
      "ocupacion_pct": 0.004553767603300908,
      "rni": 75.86741726172926,
      "rni_v_m": 0.006213994479409377
    }
  ],
  "results_by_dane": {
    "11001": [
      {
        "fc_medida_MHz": 479.0,
        "Licencia": "NO"
      }
    ],
    "25754": [
      {
        "fc_medida_MHz": 479.0,
        "Licencia": "SI"
      }
    ]
  }
}
```

## Campos de primer nivel que usa el backend

- `mode`
  debe venir como `"compliance"`

- `cumplimiento`
  debe venir como `1`

- `num_emissions`
  cantidad de emisiones detectadas en ese frame

- `results`
  lista principal de emisiones evaluadas

- `results_by_dane`
  mapa opcional por DANE; el backend lo usa para intentar autorizar emisiones en municipios adyacentes

- `umbral_db`
  umbral relativo que se mando desde backend

- `umbral`
  umbral absoluto realmente usado por el motor

- `danes`
  lista de DANEs evaluados cuando el request incluyo varios

## Estructura de cada item en `results`

Cada elemento de `results` representa una emision ya medida y comparada contra licencias.

Campos principales:

- `fc_medida_MHz`
- `fc_nominal_MHz`
- `delta_f_MHz`
- `bw_medido_kHz`
- `bw_nominal_kHz`
- `delta_bw_kHz`
- `p_medida_dBm`
- `p_nominal_dBm`
- `delta_p_dB`
- `Cumple_FC`
- `Cumple_BW`
- `Cumple_P`
- `Licencia`

Campos opcionales adicionales:

- `mer_db`
- `ber_est`
- `ocupacion_pct`
- `rni`
- `rni_v_m`

## Significado de los campos normativos

- `Licencia`
  `"SI"` si hubo match con licencia
  `"NO"` si no hubo match

- `Cumple_FC`
  `"SI"` o `"NO"` segun la tolerancia de frecuencia central

- `Cumple_BW`
  `"SI"` o `"NO"` segun la tolerancia de ancho de banda

- `Cumple_P`
  `"SI"` o `"NO"` segun la potencia nominal

- `fc_nominal_MHz`, `bw_nominal_kHz`, `p_nominal_dBm`
  valores nominales de la licencia encontrada

- `delta_f_MHz`, `delta_bw_kHz`, `delta_p_dB`
  diferencia entre la medicion y la licencia

## Cuando no hay licencia

Si no hubo match de licencia:

- `Licencia = "NO"`
- `Cumple_FC = null`
- `Cumple_BW = null`
- `Cumple_P = null`
- nominales y deltas normalmente quedan en `null`

Ejemplo:

```json
{
  "fc_medida_MHz": 479.0,
  "fc_nominal_MHz": null,
  "delta_f_MHz": null,
  "bw_medido_kHz": 5810.47,
  "bw_nominal_kHz": null,
  "delta_bw_kHz": null,
  "p_medida_dBm": -48.95,
  "p_nominal_dBm": null,
  "delta_p_dB": null,
  "Cumple_FC": null,
  "Cumple_BW": null,
  "Cumple_P": null,
  "Licencia": "NO"
}
```

## `results_by_dane`

Cuando el backend manda varios DANEs, el motor devuelve:

```json
{
  "results_by_dane": {
    "11001": [ ... ],
    "25754": [ ... ]
  }
}
```

Regla importante:

- cada clave es un DANE
- cada valor es la misma lista de emisiones, pero evaluada contra las licencias de ese DANE
- la posicion de cada emision se conserva entre DANEs

Eso le permite al backend hacer esto:

1. tomar `results` como salida base
2. si una emision sale con `Licencia = "NO"`, buscar esa misma posicion en otros DANEs
3. si en otro DANE esa emision sale con `Licencia = "SI"`, reemplazarla y marcar `_dane_autorizado`

## Lo que usa el backend para clasificar

El backend realmente se apoya en tres campos:

- `Licencia`
- `Cumple_FC`
- `Cumple_BW`

Con eso forma:

- `CUMPLE`
  si `Licencia = "SI"` y `Cumple_FC = "SI"` y `Cumple_BW = "SI"`

- `SIN_LICENCIA`
  si `Licencia = "NO"`

- `FUERA_PARAMETROS`
  si `Licencia = "SI"` pero `Cumple_FC = "NO"` o `Cumple_BW = "NO"`

Nota:

- `Cumple_P` viene en la salida de Python, pero en este backend la clasificacion final visible se arma principalmente con licencia + FC + BW.

## Ejemplo real reducido

Ejemplo tomado del flujo compliance:

```json
{
  "correction_applied": false,
  "cumplimiento": 1,
  "mode": "compliance",
  "num_emissions": 1,
  "picos": [],
  "picos_count": 0,
  "results": [
    {
      "Cumple_BW": null,
      "Cumple_FC": null,
      "Cumple_P": null,
      "Licencia": "NO",
      "bw_medido_kHz": 5810.479594389737,
      "fc_medida_MHz": 479.0,
      "mer_db": 3.4100500428919376,
      "ber_est": 0.12501813547159088,
      "p_medida_dBm": -48.952380054447644,
      "ocupacion_pct": 0.004553767603300908,
      "rni": 75.86741726172926,
      "rni_v_m": 0.006213994479409377
    }
  ],
  "results_by_dane": {
    "11001": [
      {
        "Licencia": "NO",
        "fc_medida_MHz": 479.0
      }
    ],
    "25754": [
      {
        "Licencia": "SI",
        "fc_medida_MHz": 479.0
      }
    ]
  }
}
```

## Resumen corto

- Al backend solo le importa la salida `mode = "compliance"`.
- La lista principal viene en `results`.
- Si hay varios DANEs, la salida adicional viene en `results_by_dane`.
- Cada item de `results` trae licencia, cumplimiento normativo y valores medidos/nominales.
- El backend clasifica la emision con `Licencia`, `Cumple_FC` y `Cumple_BW`.
