"""
Unit tests for Phase 8.5: Goals-based multi-step (plan builder, goal checker, response formatter).

We mock the plan builder (return a fixed list of goals), the intent classifier
(return capability + args per call), and the goal checker (return satisfied after
one or two steps). Response formatter is mocked to return a fixed string.
RotomCore runs the goals loop and we assert on output_data and final result.
"""

import unittest
from unittest.mock import MagicMock

from app.agents.rotom_core import RotomCore
from app.capabilities.registry import CapabilityRegistry


class TestPhase85GoalsBased(unittest.TestCase):
    """Phase 8.5: RotomCore with plan_builder, goal_checker, response_formatter (all mocked)."""

    def setUp(self):
        self.registry = CapabilityRegistry()
        self.session_store = MagicMock()
        self.session_store.get.return_value = MagicMock(session_id="s1")
        self.session_memory = MagicMock()
        self.session_memory.get_context.return_value = ""
        self.intent_classifier = MagicMock()
        self.plan_builder = MagicMock()
        self.goal_checker = MagicMock()
        self.response_formatter = MagicMock()

        self.rotom = RotomCore(
            intent_classifier=self.intent_classifier,
            registry=self.registry,
            session_store=self.session_store,
            session_memory=self.session_memory,
            plan_builder=self.plan_builder,
            goal_checker=self.goal_checker,
            response_formatter=self.response_formatter,
        )

    def test_goals_path_builds_plan_and_runs_one_goal(self):
        """One goal: plan builder returns one goal; classifier returns echo; goal checker says satisfied; formatter returns final text."""
        self.plan_builder.build_plan.return_value = ["Echo the user message"]
        self.intent_classifier.classify.return_value = {"capability": "echo", "arguments": {"message": "hello"}}
        self.goal_checker.check.return_value = MagicMock(satisfied=True, output_snippet=None)
        self.response_formatter.format_response.return_value = "Here is the result: hello"

        result = self.rotom.handle("echo hello", session_id="s1")

        self.plan_builder.build_plan.assert_called_once_with("echo hello")
        self.intent_classifier.classify.assert_called_once()
        self.goal_checker.check.assert_called_once()
        self.response_formatter.format_response.assert_called_once()
        call_kw = self.response_formatter.format_response.call_args
        self.assertEqual(call_kw[0][0], "echo hello")
        self.assertEqual(len(call_kw[0][1]), 1)
        self.assertEqual(call_kw[0][1][0]["capability"], "echo")
        self.assertEqual(call_kw[0][1][0]["output"], "hello")
        self.assertEqual(call_kw[0][2], ["Echo the user message"])
        self.assertTrue(result.success)
        self.assertEqual(result.output, "Here is the result: hello")
        self.assertTrue(result.metadata.get("synthesized"))
        self.assertEqual(result.metadata.get("goals_completed"), 1)

    def test_goals_path_two_goals_two_steps(self):
        """Two goals: first goal satisfied after one run, second goal satisfied after one run; formatter called with two output_data entries."""
        self.plan_builder.build_plan.return_value = ["Get word count of text", "Echo the count"]
        self.intent_classifier.classify.side_effect = [
            {"capability": "word_count", "arguments": {"text": "one two three"}},
            {"capability": "echo", "arguments": {"message": "3"}},
        ]
        self.goal_checker.check.return_value = MagicMock(satisfied=True, output_snippet=None)
        self.response_formatter.format_response.return_value = "Word count: 3. Echoed: 3."

        result = self.rotom.handle("count words in 'one two three' and echo the count", session_id="s1")

        self.assertEqual(self.intent_classifier.classify.call_count, 2)
        self.assertEqual(self.goal_checker.check.call_count, 2)
        self.response_formatter.format_response.assert_called_once()
        output_data = self.response_formatter.format_response.call_args[0][1]
        self.assertEqual(len(output_data), 2)
        self.assertEqual(output_data[0]["capability"], "word_count")
        self.assertEqual(output_data[0]["output"], "3")
        self.assertEqual(output_data[1]["capability"], "echo")
        self.assertEqual(output_data[1]["output"], "3")
        self.assertEqual(result.metadata.get("goals_steps"), 2)
        self.assertEqual(result.metadata.get("goals_completed"), 2)

    def test_goals_path_without_plan_builder_uses_phase8(self):
        """When plan_builder is None, handle() uses the Phase 8 path (classifier on user message once)."""
        rotom_single = RotomCore(
            intent_classifier=self.intent_classifier,
            registry=self.registry,
            session_store=self.session_store,
            session_memory=self.session_memory,
            plan_builder=None,
            goal_checker=None,
            response_formatter=None,
        )
        self.intent_classifier.classify.return_value = {"capability": "echo", "arguments": {"message": "hi"}}

        result = rotom_single.handle("echo hi", session_id="s1")

        self.intent_classifier.classify.assert_called_once()
        self.assertEqual(result.capability, "echo")
        self.assertEqual(result.output, "hi")
        self.assertFalse(result.metadata.get("synthesized"))


class TestLLMPlanBuilder(unittest.TestCase):
    """LLM plan builder parses JSON array of goals; fallback to single goal on error."""

    def setUp(self):
        self.llm_client = MagicMock()
        from app.agents.plan_builder import LLMPlanBuilder
        self.builder = LLMPlanBuilder(llm_client=self.llm_client)

    def test_parses_json_array_of_goals(self):
        self.llm_client.generate.return_value = '["Goal one", "Goal two", "Goal three"]'
        plan = self.builder.build_plan("Do A, B, and C")
        self.assertEqual(plan, ["Goal one", "Goal two", "Goal three"])

    def test_invalid_json_fallback_to_single_goal(self):
        self.llm_client.generate.return_value = "not json"
        plan = self.builder.build_plan("User request")
        self.assertEqual(plan, ["User request"])

    def test_empty_list_fallback_to_single_goal(self):
        self.llm_client.generate.return_value = "[]"
        plan = self.builder.build_plan("User request")
        self.assertEqual(plan, ["User request"])


class TestLLMGoalChecker(unittest.TestCase):
    """LLM goal checker parses satisfied and optional output_snippet."""

    def setUp(self):
        self.llm_client = MagicMock()
        from app.agents.goal_checker import LLMGoalChecker
        from app.models.capability_result import CapabilityResult
        self.checker = LLMGoalChecker(llm_client=self.llm_client)
        self.result = CapabilityResult(capability="echo", output="hello", success=True, metadata={})

    def test_parses_satisfied_true(self):
        self.llm_client.generate.return_value = '{"satisfied": true, "output_snippet": null}'
        out = self.checker.check("Echo the message", "echo", self.result)
        self.assertTrue(out.satisfied)
        self.assertIsNone(out.output_snippet)

    def test_parses_satisfied_false(self):
        self.llm_client.generate.return_value = '{"satisfied": false, "output_snippet": null}'
        out = self.checker.check("Do something", "echo", self.result)
        self.assertFalse(out.satisfied)

    def test_parses_output_snippet(self):
        self.llm_client.generate.return_value = '{"satisfied": true, "output_snippet": "echoed: hello"}'
        out = self.checker.check("Echo", "echo", self.result)
        self.assertTrue(out.satisfied)
        self.assertEqual(out.output_snippet, "echoed: hello")
