"""
run_request.py — Request schema for POST /run

We use a Pydantic model so FastAPI validates the body automatically and
/docs shows a clear contract. Invalid requests get 422 before they reach
the service layer. This file is only schemas—no business logic. The API
layer (routes) converts this to the simple values the service expects
(input, session_id).
"""

from pydantic import BaseModel
from typing import Optional


class RunRequest(BaseModel):
    """
    JSON body for /run: the user's message and an optional session id.
    When session_id is present, Rotom uses it for Phase 5 context/memory.
    """

    input: str
    session_id: Optional[str] = None