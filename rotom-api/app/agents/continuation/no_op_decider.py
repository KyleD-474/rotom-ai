"""
no_op_decider.py — Phase 7: No-op continuation decider (default)

This implementation always returns done=True and no next step or final_output.
It does not call the LLM. RotomCore calls the continuation decider after every
capability run; with this no-op, the pipeline "run capability → call
continuation → return capability output" is in place but the response is
unchanged. We use it by default so we don't add an extra LLM call or change
user-visible behavior. Phase 8 can swap in the LLM decider to enable
multi-step looping.
"""

from app.agents.continuation.base_continuation_decider import BaseContinuationDecider
from app.models.capability_result import CapabilityResult
from app.models.continuation_result import ContinuationResult


class NoOpContinuationDecider(BaseContinuationDecider):
    """
    Always returns done=True; no LLM call. Used as the default so Phase 7
    does not change behavior.
    """

    def continue_(
        self,
        user_input: str,
        capability_name: str,
        result: CapabilityResult,
    ) -> ContinuationResult:
        """Return done=True and no next step or final_output."""
        return ContinuationResult(
            done=True,
            next_capability=None,
            arguments=None,
            final_output=None,
        )
