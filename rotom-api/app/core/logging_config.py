"""
logging_config.py

Centralized logging configuration for the Rotom system.

This file is responsible for:
- Defining how logs are formatted
- Ensuring logs are structured (JSON)
- Sending logs to stdout (so Docker can capture them)
- Setting the global log level

IMPORTANT:
This file should be initialized ONCE at application startup.
No other part of the system should reconfigure logging.
"""

import logging
import sys
import os
from pythonjsonlogger import jsonlogger


def setup_logging():
    """
    Configure the root logger for the entire application.

    We intentionally configure the ROOT logger so that:
    - All modules inherit this configuration automatically
    - We avoid inconsistent formatting across layers

    LOG_MODE determines formatting:
        - dev  -> human-readable logs
        - prod -> structured JSON logs
    """

    # Get the root logger instance.
    # This affects all loggers created via logging.getLogger().
    logger = logging.getLogger()

    # Set minimum logging level.
    # INFO is appropriate for production by default.
    # DEBUG can be enabled later via environment config.
    logger.setLevel(logging.INFO)

    # StreamHandler directs logs to stdout.
    # This is critical in containerized environments (Docker),
    # where stdout/stderr is how logs are collected.
    handler = logging.StreamHandler(sys.stdout)

    # JsonFormatter ensures logs are structured JSON,
    # not plain text.
    #
    # The fields listed here must match attributes
    # we inject via LoggerAdapter (request_id, layer, component).
    log_mode = os.getenv("LOG_MODE", "dev").lower()
    if log_mode == "prod":
            # Production -> structured JSON logs
            formatter = jsonlogger.JsonFormatter(
                rename_fields={
                    "levelname": "level",
                    "asctime": "timestamp"
                }
            )
    else:
        # Development -> clean readable logs
        formatter = logging.Formatter(
            "[%(levelname)s] %(message)s"
        )


    handler.setFormatter(formatter)

    # Remove any existing handlers to avoid duplicate logs.
    logger.handlers = []

    # Attach our configured handler.
    logger.addHandler(handler)