"""
Unit tests for Phase 5, Phase 6, and goals-based flow: RotomCore's use of session memory,
reference resolution, and the goals path.

We use a real CapabilityRegistry and a real capability (echo), but we mock
the session_store, session_memory, intent_classifier, plan_builder, goal_checker,
and response_formatter. That lets us verify:
  1. When session_id is set, RotomCore calls get_context(session_id, max_turns=5)
     and the goals path runs (plan → classify per goal → execute → goal_checker).
  2. After handling the request, RotomCore calls append() for user entry and
     assistant entry; the user entry is always the original user_input.
  3. When session_id is None, RotomCore does not call get_context or append.
  4. Phase 6: When reference_resolver is present and context is non-empty, we call
     the resolver; memory still stores the original user message.
No real LLM or memory backend is used—only mocks.
"""

import unittest
from unittest.mock import MagicMock

from app.agents.rotom_core import RotomCore
from app.capabilities.registry import CapabilityRegistry  # includes EchoCapability


def _make_goals_mocks():
    """Return (plan_builder, goal_checker, response_formatter) mocks for goals-based flow."""
    plan_builder = MagicMock()
    plan_builder.build_plan.return_value = [{"goal": "echo the message"}]

    goal_checker = MagicMock()
    goal_checker.check.return_value = MagicMock(satisfied=True, output_snippet=None)

    response_formatter = MagicMock()
    response_formatter.format_response.side_effect = (
        lambda user_input, output_data, goal_strings: (
            output_data[-1].get("output", "") if output_data else ""
        )
    )

    return plan_builder, goal_checker, response_formatter


class TestRotomCoreMemory(unittest.TestCase):
    """
    We test RotomCore by giving it mostly fake dependencies (mocks) and one real
    registry with the real echo capability. handle() always takes the goals path:
    build_plan → for each goal classify → execute → goal_checker → response_formatter.
    We mock plan_builder to return one goal, intent_classifier to return echo/hello,
    goal_checker to say satisfied, and response_formatter to return the last output.
    """

    def setUp(self):
        self.registry = CapabilityRegistry()
        self.session_store = MagicMock()
        self.session_store.get.return_value = MagicMock(session_id="s1")
        self.session_memory = MagicMock()
        self.session_memory.get_context.return_value = ""

        self.intent_classifier = MagicMock()
        self.intent_classifier.classify.return_value = {
            "capability": "echo",
            "arguments": {"message": "hello"},
        }

        self.plan_builder, self.goal_checker, self.response_formatter = _make_goals_mocks()

        self.rotom = RotomCore(
            intent_classifier=self.intent_classifier,
            registry=self.registry,
            session_store=self.session_store,
            session_memory=self.session_memory,
            plan_builder=self.plan_builder,
            goal_checker=self.goal_checker,
            response_formatter=self.response_formatter,
        )

    def test_handle_with_session_id_calls_get_context_and_classify_with_goal(self):
        """With a session_id, RotomCore gets context and the goals path runs; classifier is called with goal text and context."""
        self.session_memory.get_context.return_value = "User: previous message"
        result = self.rotom.handle("echo hello", session_id="s1")
        self.session_memory.get_context.assert_called_once_with("s1", max_turns=5)
        # Classify is called from _handle_goals_based with (goal_text, step_context).
        self.intent_classifier.classify.assert_called()
        call_args = self.intent_classifier.classify.call_args
        self.assertEqual(call_args[0][0], "echo the message")
        self.assertTrue(result.success)
        self.assertEqual(result.capability, "echo")

    def test_handle_with_resolver_rewrites_and_goals_path_runs(self):
        """Phase 6: With session_id, context, and reference_resolver, resolve() is called; then goals path runs."""
        self.session_memory.get_context.return_value = "User: echo hi\nAssistant: ran echo, result: hi"
        resolver = MagicMock()
        resolver.resolve.return_value = "echo hello"
        plan_builder, goal_checker, response_formatter = _make_goals_mocks()
        rotom_with_resolver = RotomCore(
            intent_classifier=self.intent_classifier,
            registry=self.registry,
            session_store=self.session_store,
            session_memory=self.session_memory,
            plan_builder=plan_builder,
            goal_checker=goal_checker,
            response_formatter=response_formatter,
            reference_resolver=resolver,
        )
        result = rotom_with_resolver.handle("do that again", session_id="s1")
        resolver.resolve.assert_called_once_with(
            "do that again",
            "User: echo hi\nAssistant: ran echo, result: hi",
        )
        # Plan is built from the resolved message, not the raw user input.
        plan_builder.build_plan.assert_called_once_with("echo hello")
        self.assertTrue(result.success)

    def test_handle_with_resolver_appends_original_user_message(self):
        """Phase 6: Memory must store the original user message, not the rewritten one."""
        self.session_memory.get_context.return_value = "User: echo hi"
        resolver = MagicMock()
        resolver.resolve.return_value = "echo hello"
        plan_builder, goal_checker, response_formatter = _make_goals_mocks()
        rotom_with_resolver = RotomCore(
            intent_classifier=self.intent_classifier,
            registry=self.registry,
            session_store=self.session_store,
            session_memory=self.session_memory,
            plan_builder=plan_builder,
            goal_checker=goal_checker,
            response_formatter=response_formatter,
            reference_resolver=resolver,
        )
        rotom_with_resolver.handle("do that again", session_id="s1")
        calls = self.session_memory.append.call_args_list
        self.assertEqual(calls[0][0][1], {"role": "user", "content": "do that again"})

    def test_handle_with_session_id_appends_user_and_assistant_entries(self):
        """After execution, RotomCore should append the user message and a short assistant summary."""
        self.rotom.handle("echo hello", session_id="s1")
        self.assertEqual(self.session_memory.append.call_count, 2)
        calls = self.session_memory.append.call_args_list
        self.assertEqual(calls[0][0][0], "s1")
        self.assertEqual(calls[0][0][1], {"role": "user", "content": "echo hello"})
        self.assertEqual(calls[1][0][0], "s1")
        self.assertEqual(calls[1][0][1]["role"], "assistant")
        self.assertEqual(calls[1][0][1]["capability"], "echo")
        self.assertEqual(calls[1][0][1]["output_summary"], "hello")

    def test_handle_without_session_id_does_not_call_get_context_or_append(self):
        """Stateless requests (no session_id) must not touch memory."""
        self.rotom.handle("echo hello", session_id=None)
        self.session_memory.get_context.assert_not_called()
        self.session_memory.append.assert_not_called()
        self.intent_classifier.classify.assert_called()
