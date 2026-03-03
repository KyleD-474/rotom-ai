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
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)

    log_mode = os.getenv("LOG_MODE", "dev").lower()
    if log_mode == "prod":
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"levelname": "level", "asctime": "timestamp"},
            datefmt="%H:%M:%S"
        )
    else:
        # formatter = logging.Formatter("[%(levelname)s] %(name)s %(filename)s:%(lineno)d | %(message)s")
        formatter = logging.Formatter(
            "[%(levelname)s] %(asctime)s %(filename)s:%(lineno)d | %(message)s",
            datefmt="%H:%M:%S"
        )

    handler.setFormatter(formatter)
    logger.handlers = []
    logger.addHandler(handler)

    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("langchain_core").setLevel(logging.WARNING)
    logging.getLogger("langchain_openai").setLevel(logging.WARNING)
    logging.getLogger("langchain_community").setLevel(logging.WARNING)
    logging.getLogger("langchain_community.tools").setLevel(logging.WARNING)
    logging.getLogger("langchain_community.tools.base").setLevel(logging.WARNING)
    logging.getLogger("langchain_community.tools.base.tool").setLevel(logging.WARNING)
    logging.getLogger("langchain_community.tools.base.tool.tool").setLevel(logging.WARNING)