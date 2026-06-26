from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping, Optional, Tuple


@dataclass(frozen=True)
class DetectorUserControls:
    """Estructura preparada para exponer controles finos al usuario mas adelante.

    Importante:
    - Hoy el servidor no consume estos campos.
    - Este modulo solo deja listo el contrato interno para conectarlo despues
      sin redisenar otra vez los nombres ni el mapeo a overrides.
    """

    simple_preset_name: Optional[str] = None
    threshold_margin_db: Optional[float] = None
    min_prominence_db: Optional[float] = None
    min_support_ratio: Optional[float] = None
    min_bandwidth_hz: Optional[float] = None
    max_gap_hz: Optional[float] = None
    smooth_sigma_bins: Optional[float] = None
    local_baseline_window_hz: Optional[float] = None
    grow_threshold_relax_db: Optional[float] = None
    seed_prominence_db: Optional[float] = None
    edge_prominence_db: Optional[float] = None
    slow_rescue_window_scale: Optional[float] = None
    slow_rescue_delta_db: Optional[float] = None
    slow_rescue_peak_prominence_db: Optional[float] = None
    slow_rescue_max_width_factor: Optional[float] = None
    slow_rescue_gap_hz: Optional[float] = None
    slow_rescue_max_existing_segments: Optional[float] = None


FUTURE_USER_CONTROL_FIELDS: Dict[str, Dict[str, str]] = {
    "simple_preset_name": {
        "type": "string",
        "description": "Perfil interno del detector simple: general, fm_dense, high_res o uhf_tv.",
    },
    "threshold_margin_db": {
        "type": "float",
        "description": "Margen del umbral absoluto sobre el piso de ruido.",
    },
    "min_prominence_db": {
        "type": "float",
        "description": "Prominencia minima para aceptar un segmento.",
    },
    "min_support_ratio": {
        "type": "float",
        "description": "Fraccion minima de soporte util dentro del segmento.",
    },
    "min_bandwidth_hz": {
        "type": "float",
        "description": "Ancho minimo aceptado para una emision candidata.",
    },
    "max_gap_hz": {
        "type": "float",
        "description": "Hueco maximo que se puede cerrar al consolidar segmentos.",
    },
    "smooth_sigma_bins": {
        "type": "float",
        "description": "Suavizado gaussiano previo a la deteccion.",
    },
    "local_baseline_window_hz": {
        "type": "float",
        "description": "Ventana de baseline local para el residual principal.",
    },
    "grow_threshold_relax_db": {
        "type": "float",
        "description": "Relajacion del umbral durante la expansion de segmentos.",
    },
    "seed_prominence_db": {
        "type": "float",
        "description": "Umbral de siembra sobre el residual local.",
    },
    "edge_prominence_db": {
        "type": "float",
        "description": "Umbral de borde para crecimiento y soporte.",
    },
    "slow_rescue_window_scale": {
        "type": "float",
        "description": "Escala de baseline lenta para rescate en trazas dominadas por agujas finas.",
    },
    "slow_rescue_delta_db": {
        "type": "float",
        "description": "Delta de residual lento requerido para rescatar segmentos.",
    },
    "slow_rescue_peak_prominence_db": {
        "type": "float",
        "description": "Prominencia minima del rescate lento.",
    },
    "slow_rescue_max_width_factor": {
        "type": "float",
        "description": "Multiplo del ancho minimo permitido para rescate lento.",
    },
    "slow_rescue_gap_hz": {
        "type": "float",
        "description": "Gap maximo del rescate lento.",
    },
    "slow_rescue_max_existing_segments": {
        "type": "float",
        "description": "Cantidad maxima de segmentos previos para habilitar el rescate lento.",
    },
}


def coerce_user_controls(raw: Optional[Mapping[str, Any]]) -> Optional[DetectorUserControls]:
    if raw is None:
        return None

    data: Dict[str, Any] = {}
    for key in DetectorUserControls.__dataclass_fields__.keys():
        if key not in raw or raw[key] is None:
            continue
        if key == "simple_preset_name":
            data[key] = str(raw[key]).strip().lower() or None
        else:
            data[key] = float(raw[key])
    return DetectorUserControls(**data)


def resolve_simple_detector_controls(
    controls: Optional[Mapping[str, Any] | DetectorUserControls],
) -> Tuple[Optional[str], Dict[str, float]]:
    """Convierte el contrato futuro del usuario al formato de overrides interno.

    Esta funcion no se usa todavia desde el servidor. Queda lista para cuando se
    agregue el flujo HTTP/CLI que permita exponer estos controles.
    """

    if controls is None:
        return None, {}

    typed = controls if isinstance(controls, DetectorUserControls) else coerce_user_controls(controls)
    if typed is None:
        return None, {}

    data = asdict(typed)
    preset_name = data.pop("simple_preset_name", None)
    overrides = {k: float(v) for k, v in data.items() if v is not None}
    return preset_name, overrides
