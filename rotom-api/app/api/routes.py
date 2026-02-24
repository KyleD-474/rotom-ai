"""
routes.py

Defines the HTTP API surface for Rotom.

This layer is responsible ONLY for:
- Accepting HTTP requests
- Validating request structure
- Calling service layer
- Returning HTTP responses

It should NOT:
- Contain business logic
- Perform routing decisions
- Instantiate agents directly
"""

from app.services.agent_service import AgentService
from app.core.logger import get_logger
from app.schemas.run_request import RunRequest
from app.schemas.run_response import RunResponse
from fastapi import APIRouter

router = APIRouter()

# Create a logger scoped to the API layer
logger = get_logger(__name__, layer="api", component="routes")

# Service instance (stateless wrapper around agent orchestration)
agent_service = AgentService()


@router.get("/health")
def health_check():
    """
    Simple health check endpoint.

    Used for:
    - Docker health checks
    - Infrastructure verification
    - Monitoring systems
    """
    logger.debug("Health check invoked")

    return {"status": "ok"}


@router.post("/run", response_model=RunResponse)
def run_agent(request: RunRequest):
    """
    Primary execution endpoint.

    Expects:
        {
            "input": "some text"
        }

    Delegates execution to the service layer.
    """
    logger.debug("Run endpoint called")

    result = agent_service.run(
        user_input=request.input,
        session_id=request.session_id
    )

    logger.debug("Run endpoint completed")

    return result