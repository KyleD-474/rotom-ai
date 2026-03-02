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

        logger.debug(
            f"Building prompt for continuation decider.\n"+
            f"User input:\n{user_input}\n"+ 
            f"Capability name:\n{capability_name}\n"+
            f"Result output:\n{result.output}\n"+
            f"Result metadata:\n{result.metadata}\n",
        )

        prompt = self._build_prompt(user_input, capability_name, result)
        logger.debug(f"Prompt for llm continuation decider:\n{prompt}")

        raw = self.llm_client.generate(prompt)
        logger.debug(f"Raw output (response) from llm continuation decider:\n{raw}")

        parsed = self._parse_response(raw)
        logger.debug(f"Parsed output (response) from llm continuation decider:\n{json.dumps(parsed, indent=4)}")
        
        return parsed

    def _build_prompt(
        self,
        user_input: str,
        capability_name: str,
        result: CapabilityResult,
    ) -> str:
        """Ask the LLM to return only valid JSON in the continuation shape. Include available capabilities so next_capability must be one of them."""
        output_summary = (result.output or "")[:RESULT_SUMMARY_MAX_LEN]
        capabilities_block = self._format_capabilities_block()
        # Keep user message in prompt but put multi-step rule first so the model sees it before the long text.
        return f"""You are a continuation decider. Reply with ONLY valid JSON, no other text.

RULE: If the user asked for MORE THAN ONE thing (e.g. "summarize AND word count" or "summarize then count words in the summary"), you MUST return done=false until ALL steps are done. After only ONE capability has run, if the user's message mentions multiple actions, return done=false and set next_capability and arguments for the next step. Return done=true ONLY when every part of the user's request has been completed.

JSON shape:
{{
  "done": true or false,
  "next_capability": null or "<capability_name>",
  "arguments": null or {{ "<arg_name>": <value> }},
  "final_output": null or "<synthesized reply to user>"
}}

- If done is false: next_capability must be one of the capability names below; arguments must match that capability's schema. Use the previous step's result as input when the next step needs it (e.g. word_count on the summarizer's output).
- If done is true: set next_capability and arguments to null. Optionally set final_output to a combined reply for the user.
{capabilities_block}
Capability that just ran: {capability_name}
Result output from that step: {output_summary}

User's full message:
{user_input}

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
            logger.warning(
                "Continuation LLM returned invalid JSON; defaulting to done=True",
                extra={"error": str(e), "raw_preview": (raw or "")[:300]},
            )
            return ContinuationResult(done=True, next_capability=None, arguments=None, final_output=None)
        # If the LLM provided a next step, treat as not done even if "done" is missing or wrong.
        next_cap = data.get("next_capability")
        done = data.get("done", None)
        if not isinstance(done, bool):
            done = None
        if done is None:
            done = not (next_cap and isinstance(next_cap, str) and next_cap.strip())
        if not isinstance(done, bool):
            done = True
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
