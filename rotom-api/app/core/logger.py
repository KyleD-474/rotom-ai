"""
logger.py

This module provides a structured logging wrapper
around Python's standard logging module.

Why not just use logging.getLogger() directly?

Because we want:
- Automatic injection of request_id
- Automatic injection of architectural layer
- Automatic injection of component name
- Consistent log metadata across the system

We accomplish this using logging.LoggerAdapter.
"""

import logging
from app.core.context import get_request_id


"""
Custom LoggerAdapter that injects structured fields
into every log message.

Fields automatically added:
- request_id (from contextvars)
- layer (api / service / agent / capability)
- component (specific file or logical module)
"""
class RotomLoggerAdapter(logging.LoggerAdapter):
    """
    Called internally every time a log method is invoked.

    We use this to inject structured fields
    into the 'extra' dictionary.
    """
    def process(self, msg, kwargs):

        # Ensure an 'extra' dict exists
        extra = kwargs.setdefault("extra", {})

        # Inject request_id from context
        extra.setdefault("request_id", get_request_id())

        # Inject architectural metadata
        extra.setdefault("layer", self.extra.get("layer"))
        extra.setdefault("component", self.extra.get("component"))

        return msg, kwargs

"""
Factory function for creating a properly configured logger.

Arguments:
- name: usually __name__
- layer: architectural layer ("api", "service", "agent", etc.)
- component: logical component name

Example:
    logger = get_logger(__name__, "agent", "rotom_core")
"""
def get_logger(name: str, layer: str, component: str):
    base_logger = logging.getLogger(name)

    return RotomLoggerAdapter(
        base_logger,
        {"layer": layer, "component": component}
    )