"""
base_continuation_decider.py — Phase 7: Abstract interface for continuation after a capability run

A continuation decider has one job: given the user message, the capability
that just ran, and its result, return a structured decision (done? next step?
optional synthesized output). It does not run capabilities or touch session
state—it only produces the ContinuationResult. RotomCore calls this after
every capability execution; with a no-op implementation the response to the
user is unchanged (capability output). With an LLM implementation, Phase 8
can use the structured output to loop or to return a synthesized reply.
"""

from abc import ABC, abstractmethod
from app.models.capability_result import CapabilityResult
from app.models.continuation_result import ContinuationResult


class BaseContinuationDecider(ABC):
    """
    Implementations take (user_input, capability_name, result) and return a
    ContinuationResult (done, optional next_capability/arguments, optional
    final_output). No capability execution or session logic—pure decision.
    """

    @abstractmethod
    def continue_(
        self,
        user_input: str,
        capability_name: str,
        result: CapabilityResult,
    ) -> ContinuationResult:
        """
        Decide what to do after a capability has run.

        Args:
            user_input: The original user message.
            capability_name: Name of the capability that ran.
            result: The CapabilityResult from that run (output, success, metadata).

        Returns:
            A ContinuationResult: done (required), and optionally
            next_capability, arguments, final_output. Phase 7 ignores these
            for the response; Phase 8 will use them to loop or synthesize.
        """
        pass
