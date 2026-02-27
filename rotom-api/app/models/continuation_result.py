"""
continuation_result.py — Phase 7: Structured continuation after a capability run

After a capability executes, we may pass its result to a "continuation decider"
(e.g. an LLM) that returns a structured decision: are we done? should we run
another capability? optionally, a synthesized final reply? This model is the
contract for that decision. Phase 8 will use `done` and `next_capability` to
run a multi-step loop; Phase 7 only establishes the call site and ignores the
return for the response (we still return the capability output).
"""

from pydantic import BaseModel
from typing import Dict, Any, Optional


class ContinuationResult(BaseModel):
    """
    Structured decision returned by the continuation decider after a capability run.

    - done: True means we are done (single step or end of loop). False means
      Phase 8 should run next_capability with arguments.
    - next_capability / arguments: Used in Phase 8 to run another capability
      without a new user message.
    - final_output: Optional synthesized reply; in Phase 7 we do not use it—
      we always return the capability output. Later we can opt in when the
      decider explicitly provides a final_output.
    """

    done: bool
    next_capability: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    final_output: Optional[str] = None
