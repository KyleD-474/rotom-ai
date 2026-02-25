"""
logger.py — Structured logging for Rotom

We wrap Python's standard logging with a LoggerAdapter so that every log
message automatically gets extra fields: request_id (from contextvars),
layer (e.g. "api", "agent", "capability"), and component (e.g. "rotom_core").
That way you can filter or search logs by request or by part of the system
without every call site having to pass these manually.

Usage: get_logger(__name__, layer="agent", component="rotom_core"), then
logger.info("message") or logger.debug("message") as usual.
"""

import logging
from app.core.context import get_request_id


class RotomLoggerAdapter(logging.LoggerAdapter):
    """
    Injects request_id, layer, and component into the 'extra' dict for every
    log call. The formatter (see logging_config.py) can then include these
    in the output (e.g. JSON in production).
    """

    def process(self, msg, kwargs):
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("request_id", get_request_id())
        extra.setdefault("layer", self.extra.get("layer"))
        extra.setdefault("component", self.extra.get("component"))
        return msg, kwargs


def get_logger(name: str, layer: str, component: str):
    """Create a logger that automatically tags all messages with the given layer and component."""
    base_logger = logging.getLogger(name)
    return RotomLoggerAdapter(base_logger, {"layer": layer, "component": component})