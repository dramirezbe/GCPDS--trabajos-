"""!
@file __init__.py
@brief Initializes the libs package and exposes its key components.
@details This file makes the 'libs' directory a Python package and provides
         easy access to the ProcessingMonitor, socket handling functions,
         and the configured loggers.
"""


# Expose the configured loggers from the central config
from .logger_config import backend_logger, processing_logger