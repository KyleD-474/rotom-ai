"""
run_request.py

Defines the request schema for the /run endpoint.

Why this file exists:

Previously, the API accepted a raw dictionary (payload: dict),
which caused the following issues:

- No input validation
- No auto-generated API documentation clarity
- Swagger showed generic "additionalProp1" schema
- No type enforcement
- Harder to maintain as the API evolves

By defining a Pydantic model, we gain:

- Automatic request validation
- Clear API documentation in /docs
- Strong typing
- Automatic 422 errors for malformed input
- Cleaner service-layer contracts

This file contains ONLY schema definitions.
It should not contain business logic.
"""

from pydantic import BaseModel
from typing import Optional


class RunRequest(BaseModel):
    """
    Schema for incoming /run requests.

    Expected JSON body:

        {
            "input": "some text to process"
        }

    Attributes:
        input (str):
            The raw user input string that will be processed
            by RotomCore and routed to the appropriate capability.

    Future extensibility:

        This schema can be expanded later to include:
            - session_id
            - user_id
            - metadata
            - execution options
            - model selection overrides
    """

    input: str
    session_id: Optional[str] = None