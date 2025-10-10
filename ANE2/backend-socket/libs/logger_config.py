"""!
@file logger_config.py
@brief Centralized logging configuration for the application.
@details This module sets up two distinct loggers:
         - 'backend': For general application logs, decorated with '[Backend]'.
         - 'processing': For logs from the C subprocess, decorated with '[Processing]'.
         This centralized setup ensures consistent log formatting across all modules.
@author GCPDS
"""

import logging

def setup_logger(name, decorator, level=logging.INFO):
    """
    Sets up a logger with a custom format to include a decorator.

    @param name The name of the logger.
    @param decorator The string decorator to prepend to messages (e.g., '[Backend]').
    @param level The logging level.
    @return A configured logger instance.
    """
    # Create a custom formatter
    formatter = logging.Formatter(f"{decorator} %(message)s")
    
    # Create a handler to output to the console
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    # Get the logger and configure it
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding handlers multiple times if this function is called again
    if not logger.handlers:
        logger.addHandler(handler)
        
    return logger

# Create and export the logger instances for the application to use
backend_logger = setup_logger('backend', '[Backend]')
processing_logger = setup_logger('processing', '[Processing]')