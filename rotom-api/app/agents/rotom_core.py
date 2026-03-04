"""
rotom_core.py — The main orchestrator

RotomCore is the "brain" that orchestrates the goals-based flow: build a plan
(list of goals), then for each goal run intent classifier(goal, context) →
capability → goal_checker; accumulate output_data; when all goals satisfied,
response_formatter produces final output. It does NOT construct any of its
dependencies—those are injected by the service layer.

Phase 5: When a session_id is present, we read recent conversation from
session_memory. After execution we append this turn (user message + what we ran +
short result summary) to session_memory for the next request. Capabilities
never see session or memory—only RotomCore talks to memory.

Phase 6: When session_id and context exist and a reference_resolver is injected,
we can rewrite the user message (resolve "that", "it", "again" from context)
before building the plan. We still append the original user_input to memory.

Goal_checker decides per-goal satisfaction (retry or advance); there is no
plan-free continuation decider—we always use the goals-based path.
"""
import time
from typing import Dict, List, Union

from app.core.logger import get_logger
from app.models.capability_result import CapabilityResult
from app.models.plan import Plan, PlanStep, plan_goal_strings

logger = get_logger(__name__, layer="agent", component="rotom_core")

# When we store the capability result in memory we truncate output to avoid huge prompts.
OUTPUT_SUMMARY_MAX_LEN = 200

# Max total capability runs across all goals (prevents runaway execution).
MAX_GOALS_ITERATIONS = 12
# Max steps per single goal; prevents one goal from burning all iterations (e.g. goal checker never satisfied).
MAX_STEPS_PER_GOAL = 3

# Max length of an artifact value when injected into classifier context (keeps token cost bounded).
ARTIFACT_CONTEXT_MAX_LEN = 2000

# Phase 8.5: Truncation limits when building step context for the goals path (keeps token cost bounded).
GOAL_ORIGINAL_INPUT_MAX_LEN = 3500
GOAL_PREVIOUS_OUTPUT_MAX_LEN = 1000


class RotomCore:
    """
    Single entry point for "handle this user message": session/context, then
    goals-based flow (build plan → for each goal: classify → execute →
    goal_checker); record turns in memory when session_id is set.
    """

    def __init__(
        self,
        intent_classifier,
        registry,
        session_store,
        session_memory,
        plan_builder,
        goal_checker,
        response_formatter,
        reference_resolver=None,
    ):
        logger.info("Rotom Core initialized")
        self.registry = registry
        self.intent_classifier = intent_classifier
        self.session_store = session_store
        self.session_memory = session_memory
        self.plan_builder = plan_builder
        self.goal_checker = goal_checker
        self.response_formatter = response_formatter
        # Phase 6: Optional. When set, we rewrite user message from context before building plan.
        self.reference_resolver = reference_resolver

    def handle(self, user_input: str, session_id: str | None = None):
        """
        Process one user message: ensure session exists, get context from memory
        (if session), then run the goals-based flow. Phase 6 reference resolution
        runs first when session/context/resolver exist; the resolved message is
        passed into the goals flow so the plan builder can use session context.
        Memory and step context always use the original user_input.
        """
        logger.debug("Beginning handle() method.", extra={"user_input_preview": (user_input or "")[:200]})

        if session_id:
            self.session_store.get(session_id)  # Ensure session exists

        # --- Session context and reference resolution ---
        message_for_plan = self._get_context_and_message_for_classifier(session_id, user_input)

        # --- Goals-based flow (always) ---
        return self._handle_goals_based(user_input, session_id, message_for_plan=message_for_plan)

    def _handle_goals_based(
        self, user_input: str, session_id: str | None, message_for_plan: str | None = None
    ):
        """
        Phase 8.5: Build plan (goals), for each goal run classifier → capability → goal_checker,
        accumulate output_data, then response_formatter for final output.
        When message_for_plan is provided (from reference resolution), the plan is built from it;
        otherwise the plan is built from user_input. Memory and step context always use user_input.
        Uses a request-scoped artifact store when steps declare store_output_as / use_from_memory.
        """
        plan_input = message_for_plan if message_for_plan is not None else user_input
        raw_plan = self.plan_builder.build_plan(plan_input)
        steps = self._normalize_plan_to_steps(raw_plan)
        logger.debug("Goals-based plan built", extra={"goals_count": len(steps), "goals": plan_goal_strings(steps)})

        # --- Plan built; iterate over goals ---
        output_data = []
        goal_iterations = 0
        first_step_this_request = True
        artifacts: Dict[str, str] = {}

        for goal_index, step in enumerate(steps):
            if goal_iterations >= MAX_GOALS_ITERATIONS:
                logger.warning("Phase 8.5 max iterations reached; formatting with partial results")
                break
            goal_text = step["goal"]
            satisfied = False
            steps_this_goal = 0
            while not satisfied and goal_iterations < MAX_GOALS_ITERATIONS:
                # Build context for this step (original input + artifacts or previous output)
                step_context = self._build_goal_step_context(step, user_input, output_data, artifacts)

                # Classify intent for this goal
                intent_data = self.intent_classifier.classify(goal_text, context=step_context if step_context.strip() else None)
                if not self._validate_intent_data(intent_data):
                    logger.warning("Intent classifier returned invalid data for goal; skipping to next goal", extra={"goal": goal_text})
                    satisfied = True
                    break

                capability_name = intent_data["capability"]
                arguments = intent_data["arguments"]

                # Resolve capability and validate arguments
                capability = self.registry.get(capability_name)
                if not capability:
                    logger.warning("Capability not found for goal; skipping to next goal", extra={"goal": goal_text, "capability": capability_name})
                    satisfied = True
                    break

                try:
                    self._validate_arguments(capability_name, capability, arguments)
                except ValueError as e:
                    logger.warning("Invalid arguments for goal; skipping to next goal", extra={"goal": goal_text, "error": str(e)})
                    satisfied = True
                    break

                result = self._execute_capability(
                    capability_name, capability, arguments, session_id
                )

                # Record output and optional artifact
                output_data.append({
                    "goal": goal_text,
                    "capability": capability_name,
                    "output": result.output or "",
                    "success": result.success,
                })
                goal_iterations += 1
                steps_this_goal += 1

                store_key = step.get("store_output_as")
                if store_key and (k := str(store_key).strip()):
                    artifacts[k] = result.output or ""

                # Record turn in session memory
                if session_id:
                    if first_step_this_request:
                        self._append_user_turn(session_id, user_input)
                        first_step_this_request = False
                    self._append_assistant_turn(session_id, capability_name, result)

                # Check if goal is satisfied
                check_result = self.goal_checker.check(goal_text, capability_name, result)
                if check_result.output_snippet:
                    output_data[-1]["snippet"] = check_result.output_snippet
                satisfied = self._is_goal_satisfied(
                    check_result, steps_this_goal, output_data, goal_text
                )
                if satisfied and check_result.satisfied:
                    logger.debug(
                        "Goal satisfied",
                        extra={"goal": goal_text, "step": goal_iterations},
                    )

        goal_strings = plan_goal_strings(steps)
        final_output = self.response_formatter.format_response(user_input, output_data, goal_strings)
        last_cap = output_data[-1]["capability"] if output_data else "goals"
        return CapabilityResult(
            capability=last_cap,
            output=final_output,
            success=bool(output_data),
            metadata={
                "synthesized": True,
                "goals_completed": len(steps),
                "goals_steps": goal_iterations,
            },
            session_id=session_id,
        )

    def _execute_capability(
        self,
        capability_name: str,
        capability,
        arguments: dict,
        session_id: str | None,
    ):
        """
        Execute a capability with timing and error handling. Returns a CapabilityResult
        with execution_time_ms and session_id set.
        """
        start_time = time.perf_counter()
        try:
            result = capability.execute(arguments)
        except Exception as e:
            logger.error(f"Capability execution failed.\nCapability name: {capability_name}\nError: {str(e)}")
            result = CapabilityResult(
                capability=capability_name,
                output="",
                success=False,
                metadata={"error": str(e)},
            )
        end_time = time.perf_counter()
        result.metadata["execution_time_ms"] = round((end_time - start_time) * 1000, 2)
        result.session_id = session_id
        return result

    def _append_user_turn(self, session_id: str | None, user_input: str) -> None:
        """Append the user message to session memory for this turn. No-op if session_id is None."""
        if not session_id:
            return
        self.session_memory.append(session_id, {"role": "user", "content": user_input})

    def _append_assistant_turn(
        self,
        session_id: str | None,
        capability_name: str,
        result,
    ) -> None:
        """Append assistant turn (capability name + truncated output summary) to session memory. No-op if session_id is None."""
        if not session_id:
            return
        output_summary = (result.output or "")[:OUTPUT_SUMMARY_MAX_LEN]
        self.session_memory.append(
            session_id,
            {
                "role": "assistant",
                "capability": capability_name,
                "success": result.success,
                "output_summary": output_summary,
            },
        )

    def _get_context_and_message_for_classifier(self, session_id: str | None, user_input: str) -> str:
        """
        Return the message to use for the plan. When session_id, context, and
        reference_resolver are present, returns the resolved message (references
        like "that"/"it"/"again" expanded from session context); otherwise returns
        the original user_input. Callers pass this to the plan builder.
        """
        logger.debug(f"Getting context and message for plan.\nSession ID: {session_id}\nUser input: {user_input}")
        context = ""
        if session_id:
            context = self.session_memory.get_context(session_id, max_turns=5) or ""
            logger.debug(f"Context from session memory:\n{context}")

        message_for_plan = user_input
        if session_id and context.strip() and self.reference_resolver is not None:
            message_for_plan = self.reference_resolver.resolve(user_input, context)
            logger.debug(f"Reference resolver used; rewritten message:\n{message_for_plan}")
        else:
            logger.debug("No reference resolver used; returning user_input unchanged.")

        return message_for_plan

    def _build_goal_step_context(
        self,
        step: PlanStep,
        user_input: str,
        output_data: list,
        artifacts: Dict[str, str],
    ) -> str:
        """
        Build the context string for the intent classifier for one goal step.
        Uses original input (truncated), optional use_from_memory artifacts, or previous step output.
        """
        original_chunk = (user_input or "").strip()[:GOAL_ORIGINAL_INPUT_MAX_LEN]
        if not output_data:
            return original_chunk
        base = f"Original user input (use for 'the text' / 'original text' when needed):\n{original_chunk}"
        use_keys = step.get("use_from_memory")
        use_keys_list: List[str] = (
            [use_keys] if isinstance(use_keys, str) else (use_keys or [])
        )
        if use_keys_list:
            for key in use_keys_list:
                val = (artifacts.get(key) or "").strip()[:ARTIFACT_CONTEXT_MAX_LEN]
                base += f"\n\nContent of '{key}' (from a previous step):\n{val}"
        else:
            last_output = (
                (output_data[-1].get("output") or "").strip()[
                    :GOAL_PREVIOUS_OUTPUT_MAX_LEN
                ]
            )
            base += f"\n\nPrevious step result:\n{last_output}"
        return base

    def _is_goal_satisfied(
        self,
        check_result,
        steps_this_goal: int,
        output_data: list,
        goal_text: str,
    ) -> bool:
        """
        Decide if the current goal is satisfied: checker said so, max steps per goal reached,
        or duplicate step (same capability and output as previous). Logs for max steps and duplicate.
        """
        if check_result.satisfied:
            return True
        if steps_this_goal >= MAX_STEPS_PER_GOAL:
            logger.warning(
                "Per-goal step limit reached; treating goal as done",
                extra={"goal": goal_text, "steps_this_goal": steps_this_goal},
            )
            return True
        if steps_this_goal >= 2:
            last_step = output_data[-1]
            prev_step = output_data[-2]
            if (
                last_step["capability"] == prev_step["capability"]
                and (last_step.get("output") or "") == (prev_step.get("output") or "")
            ):
                logger.warning(
                    "Duplicate step for goal (same capability and output); treating as done",
                    extra={"goal": goal_text},
                )
                return True
        return False

    def _normalize_plan_to_steps(self, plan: Union[Plan, List[str]]) -> Plan:
        """Ensure we have a list of PlanStep (dicts with 'goal'). Accepts list of strings from legacy builders."""
        steps: List[PlanStep] = []
        for item in plan or []:
            if isinstance(item, str) and (s := (item or "").strip()):
                steps.append({"goal": s})
            elif isinstance(item, dict) and (item.get("goal") or item.get("description")):
                goal = (item.get("goal") or item.get("description") or "").strip()
                step: PlanStep = {"goal": goal}
                if item.get("store_output_as"):
                    step["store_output_as"] = str(item["store_output_as"]).strip()
                if item.get("use_from_memory") is not None:
                    step["use_from_memory"] = item["use_from_memory"]
                steps.append(step)
        return steps

    def _validate_intent_data(self, intent_data) -> bool:
        """
        Ensures the IntentClassifier returned a structurally valid invocation contract.
        This protects RotomCore from contract drift or misbehaving classifier implementations.
        """
        return (
            isinstance(intent_data, dict)
            and "capability" in intent_data
            and isinstance(intent_data["capability"], str)
            and intent_data["capability"].strip() != ""
            and "arguments" in intent_data
            and isinstance(intent_data["arguments"], dict)
        )

    def _validate_arguments(
        self, capability_name: str, capability, arguments: dict
    ) -> None:
        """
        Validates arguments against the capability's argument_schema before execution.

        Phase 4: Argument validation layer.
        - Every key in argument_schema must be present in arguments (required keys).
        - Arguments may only contain keys defined in argument_schema (no extra keys).

        Raises ValueError with a clear message if validation fails.
        """
        schema = getattr(capability, "argument_schema", None) or {}
        if not isinstance(schema, dict):
            raise ValueError(
                f"Capability '{capability_name}' has invalid argument_schema"
            )

        # Required: all schema keys must be present
        missing = [k for k in schema if k not in arguments]
        if missing:
            raise ValueError(
                f"Capability '{capability_name}' missing required arguments: {missing}"
            )

        # Strict: no extra keys beyond schema
        extra = [k for k in arguments if k not in schema]
        if extra:
            raise ValueError(
                f"Capability '{capability_name}' received unknown arguments: {extra}"
            )