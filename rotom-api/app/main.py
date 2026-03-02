"""
main.py — Application entry point for the Rotom API

This file is what gets run (e.g. by uvicorn). It:
  1. Loads environment from .env if present (e.g. ROTOM_CONTINUATION_MODE, OPENAI_*).
  2. Sets up logging once so every module gets consistent format and level.
  3. Creates the FastAPI app and attaches middleware that assigns each request
     a unique request_id (stored in contextvars) so logs can be traced per request.
  4. Registers the API routes (e.g. POST /run, GET /health).

We do not put business logic here—only wiring and configuration.
"""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request

from app.core.logging_config import setup_logging
from app.core.context import generate_request_id
from app.api.routes import router


# Configure logging first so anything that runs after this uses our format and level.
setup_logging()

app = FastAPI(title="Rotom AI System")


# This middleware runs on every HTTP request. It generates a unique ID for the request
# and stores it in contextvars so that logger.py can attach it to every log line
# produced while handling this request. That makes it easy to grep logs by request.
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    generate_request_id()
    response = await call_next(request)
    return response


app.include_router(router)