# Processor Default Params

Este archivo resume los defaults de la ruta activa del processor.

Cuando aplica, separa:

- parámetros efectivamente usados por la ruta viva,
- parámetros declarados en `_build_processing_args()` pero no consumidos por el call path actual.

Ruta viva:

- `process_input()`
- `_build_processing_args()`
- `_run_new_detector_on_frame()`

Fuente principal:

- `postprocesamiento/src/processor.py`
- `postprocesamiento/src/utils/region_analysis.py`

## Regla especial

- `delta_above_nf_db` usa `3.0` por defecto.
- Si llega `umbral_db`, entonces `delta_above_nf_db = max(0.0, umbral_db)`.

## Piso de ruido global

| Parámetro | Default |
| --- | ---: |
| `nf_delta_db` | `0.5` |
| `nf_percentile` | `1.0` |
| `nf_min_points` | `4` |
| `delta_above_nf_db` | `3.0` si no llega `umbral_db` |

## Suavizado

| Parámetro | Default |
| --- | ---: |
| `smooth_window` | `18` |
| `smooth_polyorder` | `2` |

Nota:

- En la práctica `_run_new_detector_on_frame()` calcula el `window_length` con `_estimate_window_length(n)`.
- Hoy ese helper retorna `20`, `16`, `10` o `7` según el número de bins del frame.

## Detección y postproceso básico

| Parámetro | Default |
| --- | ---: |
| `merge_gap_hz` | `15000.0` |
| `min_bw_hz` | `15000.0` |

## Piso de ruido dinámico por steps

Parámetros efectivamente usados hoy por `build_step_noise_floor()` desde `processor.py`:

| Parámetro | Default |
| --- | ---: |
| `refine_percentile` | `60.0` |
| `refine_expansion_factor` | `1.15` |
| `refine_height_ratio_limit` | `0.55` |

Defaults internos que `build_step_noise_floor()` usa por su propia firma en la ruta viva actual:

- `long_window_bins = max(2 * trend_window_bins + 1, 15)`
- `trend_window_bins = 9`
- `long_slope_threshold_db_per_bin = 0.01`
- `trend_slope_threshold_db_per_bin = 0.03`
- `trend_level_rise_threshold_db = 0.35`
- `trend_confirm_windows = 2`
- `trend_min_side_bins = 3`
- `trend_max_side_bins = None`
- `min_rise_ratio_vs_region_height = 0.10`
- `post_confirm_windows = 2`
- `step_overlap_policy = "max"`

Parámetros declarados en `_build_processing_args()` pero no conectados al call path actual:

- `trend_window_bins`
- `trend_slope_threshold_db_per_bin`
- `trend_level_rise_threshold_db`
- `trend_confirm_windows`
- `trend_min_side_bins`
- `trend_max_side_bins`
- `step_overlap_policy`

## Split final por valles

| Parámetro | Default |
| --- | ---: |
| `split_min_bw_hz` | `1000000.0` |
| `split_lateral_valley_height_ratio` | `0.01` |
| `split_center_valley_height_ratio` | `0.15` |
| `split_left_section_ratio` | `0.15` |
| `split_center_section_ratio` | `0.60` |
| `split_right_section_ratio` | `0.15` |
| `split_min_shoulder_drop_db` | `1.5` |
| `split_min_valley_distance_hz` | `100000.0` |
| `split_min_edge_margin_hz` | `50000.0` |

## Utilitarios

| Parámetro | Default |
| --- | ---: |
| `plot` | `False` |
| `show_expanded_windows` | `False` |
| `max_files` | `None` |
