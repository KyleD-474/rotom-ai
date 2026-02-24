"""
context.py

This module manages per-request contextual data using contextvars.

Why this exists:
- FastAPI is asynchronous.
- Multiple requests may execute concurrently.
- We need a way to store request-specific data safely.

contextvars allows us to store values that are:
- Scoped to a specific request
- Automatically isolated across concurrent async calls

In our case:
We use it to store a request_id for structured logging.
"""

import contextvars
import uuid


# Define a context variable that will hold the request_id.
# Default is None until set by middleware.
request_id_ctx = contextvars.ContextVar("request_id", default=None)


"""
Generate a new UUID for the current request
and store it in the request-scoped context.
"""
def generate_request_id():
    rid = str(uuid.uuid4())
    request_id_ctx.set(rid)
    return rid


"""
Retrieve the current request_id from context.

If called outside of a request lifecycle,
this may return None.
"""
def get_request_id():
    return request_id_ctx.get()