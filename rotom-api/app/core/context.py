"""
context.py — Per-request data using contextvars

FastAPI can handle many requests at the same time (async). We need a way to
attach data to "the current request" so that when we log something deep inside
RotomCore or a capability, we know which HTTP request it belonged to. Python's
contextvars give us exactly that: a value that is automatically isolated per
async task. The middleware (main.py) sets request_id at the start of each
request; the logger (logger.py) reads it and adds it to every log line.
"""

import contextvars
import uuid


# One context variable for the current request's ID. Defaults to None when
# we're not inside a request (e.g. during startup or in a background task).
request_id_ctx = contextvars.ContextVar("request_id", default=None)


def generate_request_id():
    """Create a new UUID, store it in context for this request, and return it. Called by middleware."""
    rid = str(uuid.uuid4())
    request_id_ctx.set(rid)
    return rid


def get_request_id():
    """Return the request_id for the current request, or None if not in a request (e.g. tests)."""
    return request_id_ctx.get()