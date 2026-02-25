"""
routes.py — HTTP API surface for Rotom

This module defines the actual HTTP endpoints. Its job is only to:
  - Accept and validate the request (using Pydantic schemas from app.schemas).
  - Call the service layer (AgentService.run) with the validated data.
  - Return the response in the shape defined by RunResponse.

We intentionally keep this thin: no business logic, no capability routing,
no direct use of RotomCore. That way the API can change (e.g. different
framework or transport) without touching orchestration or capabilities.
"""

from app.services.agent_service import AgentService
from app.core.logger import get_logger
from app.schemas.run_request import RunRequest
from app.schemas.run_response import RunResponse
from fastapi import APIRouter

router = APIRouter()
logger = get_logger(__name__, layer="api", component="routes")

# One shared service instance; it's stateless and just delegates to RotomCore.
agent_service = AgentService()


@router.get("/health")
def health_check():
    """Simple liveness check for Docker, load balancers, and monitoring. Returns 200 + {"status": "ok"}."""
    logger.debug("Health check invoked")
    return {"status": "ok"}


@router.post("/run", response_model=RunResponse)
def run_agent(request: RunRequest):
    """
    Main endpoint: send user text and optionally a session_id; get back the
    capability result (which capability ran, output, success, metadata).
    Request body: { "input": "user message", "session_id": "optional" }.
    """
    logger.debug("Run endpoint called")
    result = agent_service.run(
        user_input=request.input,
        session_id=request.session_id,
    )
    logger.debug("Run endpoint completed")
    return result