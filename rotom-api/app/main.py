"""
main.py

Application entrypoint for the Rotom API.

Responsibilities:
- Initialize logging
- Create FastAPI app
- Register middleware
- Register routes
"""

from fastapi import FastAPI, Request

from app.core.logging_config import setup_logging
from app.core.context import generate_request_id
from app.api.routes import router


# -------------------------------------------------------------------
# Initialize logging BEFORE app starts handling requests
# -------------------------------------------------------------------
setup_logging()


# -------------------------------------------------------------------
# Create FastAPI app instance
# -------------------------------------------------------------------
app = FastAPI(title="Rotom AI System")


# -------------------------------------------------------------------
# Middleware: Inject Request ID
#
# This runs on EVERY incoming HTTP request.
# It ensures that all logs generated during the lifecycle
# of this request share the same request_id.
# -------------------------------------------------------------------
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    # Generate and store request_id in contextvars
    generate_request_id()

    # Continue request processing
    response = await call_next(request)

    return response


# -------------------------------------------------------------------
# Register API routes
# -------------------------------------------------------------------
app.include_router(router)