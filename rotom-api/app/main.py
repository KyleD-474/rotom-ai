"""
main.py — Application entry point for the Rotom API

This file is what gets run (e.g. by uvicorn). It:
  1. Loads environment from .env if present (e.g. OPENAI_*, LOG_MODE).
  2. Sets up logging once so every module gets consistent format and level.
  3. Creates the FastAPI app and attaches middleware that assigns each request
     a unique request_id (stored in contextvars) so logs can be traced per request.
  4. Registers the API routes (e.g. POST /run, GET /health).

We do not put business logic here—only wiring and configuration.
"""

from pathlib import Path
from dotenv import load_dotenv

# Load .env from repo root (parent of rotom-api) so ROTOM_* and OPENAI_* are found
# when the server is run from rotom-api/ or from Docker with WORKDIR inside rotom-api.
_env_repo_root = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_repo_root)
load_dotenv()  # Also load from cwd if present (e.g. rotom-api/.env)

from app.core.logging_config import setup_logging

# Configure logging first so anything that runs after this uses our format and level.
setup_logging()

from fastapi import FastAPI, Request
from app.core.context import generate_request_id
from app.api.routes import router

app = FastAPI(title="Rotom AI System") # Create the FastAPI app.


# This middleware runs on every HTTP request. It generates a unique ID for the request
# and stores it in contextvars so that logger.py can attach it to every log line
# produced while handling this request. That makes it easy to grep logs by request.
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    generate_request_id()
    response = await call_next(request)
    return response


app.include_router(router)