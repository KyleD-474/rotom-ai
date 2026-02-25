"""
logging_config.py — One-time setup for application logging

This module configures the root logger at startup (called from main.py). We
use the root logger so every get_logger() call inherits the same format and
handler. Logs go to stdout so that in Docker (or any container) they can be
captured by the platform without touching the filesystem.

Environment:
  - LOG_MODE=dev  (default): human-readable lines like "[INFO] message".
  - LOG_MODE=prod: JSON lines so log aggregators can parse level, timestamp, request_id, etc.

The fields we use (request_id, layer, component) are injected by logger.py's
LoggerAdapter; this file only decides how they are rendered. Do not reconfigure
logging from anywhere else—do it here once at startup.
"""

import logging
import sys
import os
from pythonjsonlogger import jsonlogger


def setup_logging():
    """Configure the root logger: level, output stream, and format (dev vs prod JSON)."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    log_mode = os.getenv("LOG_MODE", "dev").lower()
    if log_mode == "prod":
        formatter = jsonlogger.JsonFormatter(
            rename_fields={"levelname": "level", "asctime": "timestamp"}
        )
    else:
        formatter = logging.Formatter("[%(levelname)s] %(message)s")

    handler.setFormatter(formatter)
    logger.handlers = []
    logger.addHandler(handler)