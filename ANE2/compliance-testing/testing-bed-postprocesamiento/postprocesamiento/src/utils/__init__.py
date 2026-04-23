"""
Utilidades para procesamiento de señales RF y detección de canales.
"""

# signal_processing
from .signal_processing import (
    smooth_psd,
    estimate_local_trend,
    find_local_minima_indices
)

# noise_floor
from .noise_floor import detect_noise_floor_from_psd

# channel_detection
from .channel_detection import (
    detect_channels_from_psd,
    detect_channels_from_variable_threshold,
    merge_and_filter_regions,
    contiguous_regions
)

# region_analysis
from .region_analysis import (
    split_wide_regions_by_internal_valleys,
    split_one_region_by_valleys,
    get_adaptive_valley_height_ratio,
    expand_region_by_factor,
    expand_region_adaptively,
    deduplicate_close_valleys,
    find_adaptive_expansion_bins,
    apply_step_nf_on_interval,
    build_step_noise_floor
)

# io_visualization
from .io_visualization import (
    read_psd_json,
    plot_psd_result
)

__all__ = [
    # signal_processing
    "smooth_psd",
    "estimate_local_trend",
    "find_local_minima_indices",
    
    # noise_floor
    "detect_noise_floor_from_psd",
    
    # channel_detection
    "detect_channels_from_psd",
    "detect_channels_from_variable_threshold",
    "merge_and_filter_regions",
    "contiguous_regions",
    
    # region_analysis
    "split_wide_regions_by_internal_valleys",
    "split_one_region_by_valleys",
    "get_adaptive_valley_height_ratio",
    "expand_region_by_factor",
    "expand_region_adaptively",
    "deduplicate_close_valleys",
    "find_adaptive_expansion_bins",
    "apply_step_nf_on_interval",
    "build_step_noise_floor",
    
    # io_visualization
    "read_psd_json",
    "plot_psd_result",
]