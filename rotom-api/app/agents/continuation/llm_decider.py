"""
llm_decider.py — Phase 7: LLM-backed continuation decider (optional; for Phase 8)

After a capability runs, this implementation sends the user message, capability
name, and result summary to the LLM and asks for a structured JSON response:
done, next_capability, arguments, final_output. We parse and return a
ContinuationResult. Used in tests and in Phase 8 when we enable multi-step
looping; the default in Phase 7 production is NoOpContinuationDecider so we
don't add an extra LLM call.
"""

import json
from app.agents.continuation.base_continuation_decider import BaseContinuationDecider
from app.agents.llm.base_llm_client import BaseLLMClient
from app.models.capability_result import CapabilityResult
from app.models.continuation_result import ContinuationResult
from app.core.logger import get_logger

logger = get_logger(__name__, layer="agent", component="continuation")

# Truncate result output in the prompt to avoid huge payloads.
RESULT_SUMMARY_MAX_LEN = 500


class LLMContinuationDecider(BaseContinuationDecider):
    """
    Calls the LLM with user message, capability name, and result; expects
    JSON back with done (required) and optional next_capability, arguments,
    final_output. Returns a ContinuationResult. Requires tool_metadata
    (same shape as intent classifier: list of {name, description, arguments})
    so the prompt can list available capabilities—when done is false,
    next_capability must be one of these names and arguments must match.
    """

    def __init__(self, llm_client: BaseLLMClient, tool_metadata: list[dict] | None = None):
        self.llm_client = llm_client
        self.tool_metadata = tool_metadata or []

    def continue_(
        self,
        user_input: str,
        capability_name: str,
        result: CapabilityResult,
    ) -> ContinuationResult:
        """Build prompt, call LLM, parse JSON into ContinuationResult."""
        prompt = self._build_prompt(user_input, capability_name, result)
        raw = self.llm_client.generate(prompt)
        return self._parse_response(raw)

    def _build_prompt(
        self,
        user_input: str,
        capability_name: str,
        result: CapabilityResult,
    ) -> str:
        """Ask the LLM to return only valid JSON in the continuation shape. Include available capabilities so next_capability must be one of them."""
        output_summary = (result.output or "")[:RESULT_SUMMARY_MAX_LEN]
        capabilities_block = self._format_capabilities_block()
        return f"""You are a continuation decider. Given the user's message, the capability that just ran, and its result, respond with ONLY valid JSON in this exact shape (no explanation, no markdown):

{{
  "done": true or false,
  "next_capability": null or "<capability_name>",
  "arguments": null or {{ "<arg_name>": <value> }},
  "final_output": null or "<synthesized reply to user>"
}}

Rules:
- "done" is required. true = we are done (single step or end of loop). false = another capability should run (provide next_capability and arguments).
- If done is false, next_capability MUST be exactly one of the available capability names listed below, and arguments MUST match that capability's schema.
- If done is true, set next_capability and arguments to null unless you have a specific next step.
- final_output: only set if you are synthesizing a reply for the user; otherwise null. We prefer to return the capability output unchanged.
{capabilities_block}
User message: {user_input}
Capability that ran: {capability_name}
Success: {result.success}
Result output: {output_summary}

JSON only:"""

    def _format_capabilities_block(self) -> str:
        """Format the list of available capabilities for the prompt so the LLM only chooses from these."""
        if not self.tool_metadata:
            return "\nAvailable capabilities: (none—if done is false, you have no valid next step; prefer done true.)\n"
        lines = ["\nAvailable capabilities (if done is false, next_capability must be one of these):"]
        for tool in self.tool_metadata:
            lines.append(f"\n  - {tool.get('name', '?')}: {tool.get('description', '')}")
            args = tool.get("arguments") or {}
            for arg_name, arg_desc in args.items():
                lines.append(f"    Argument: {arg_name} — {arg_desc}")
        return "\n".join(lines) + "\n"

    def _parse_response(self, raw: str) -> ContinuationResult:
        """Parse LLM JSON into ContinuationResult; defensively handle missing fields."""
        raw = (raw or "").strip()
        # Strip markdown code fence if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("Continuation LLM returned invalid JSON; defaulting to done=True", extra={"error": str(e)})
            return ContinuationResult(done=True, next_capability=None, arguments=None, final_output=None)
        done = data.get("done", True)
        if not isinstance(done, bool):
            done = True
        next_cap = data.get("next_capability")
        if next_cap is not None and not isinstance(next_cap, str):
            next_cap = None
        # If the LLM returned a next_capability that isn't in our registry, ignore it (stay done).
        valid_names = [t.get("name") for t in self.tool_metadata if t.get("name")]
        if next_cap and valid_names and next_cap not in valid_names:
            logger.warning("Continuation LLM returned unknown capability; treating as done", extra={"next_capability": next_cap, "valid": valid_names})
            next_cap = None
            done = True
        args = data.get("arguments")
        if args is not None and not isinstance(args, dict):
            args = None
        final = data.get("final_output")
        if final is not None and not isinstance(final, str):
            final = None
        return ContinuationResult(
            done=done,
            next_capability=next_cap,
            arguments=args,
            final_output=final,
        )
