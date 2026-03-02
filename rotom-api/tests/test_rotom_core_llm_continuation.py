"""
Unit tests for Phase 8: RotomCore with LLMContinuationDecider (mocked LLM).

We wire the real LLMContinuationDecider and a real CapabilityRegistry (echo,
summarizer_stub, word_count) into RotomCore, but mock the LLM client's generate()
so no real API is called. This verifies that multi-step flows driven by the
LLM decider work end-to-end: two-step, three-step, and final_output synthesis.
"""

import unittest
from unittest.mock import MagicMock

from app.agents.rotom_core import RotomCore
from app.agents.continuation import LLMContinuationDecider
from app.capabilities.registry import CapabilityRegistry


class TestRotomCoreLLMContinuation(unittest.TestCase):
    """
    RotomCore + real LLMContinuationDecider + mocked llm_client.generate().
    Real registry (echo, summarizer_stub stub, word_count) so capabilities actually run.
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
        self.llm_client = MagicMock()
        self.decider = LLMContinuationDecider(
            llm_client=self.llm_client,
            tool_metadata=self.registry.list_metadata(),
        )
        self.rotom = RotomCore(
            intent_classifier=self.intent_classifier,
            registry=self.registry,
            session_store=self.session_store,
            session_memory=self.session_memory,
            continuation_decider=self.decider,
        )

    def test_two_step_echo_then_echo_llm_decider(self):
        """Two steps: echo('hello') then continuation says run echo('second'); decider then says done."""
        self.llm_client.generate.side_effect = [
            '{"done": false, "next_capability": "echo", "arguments": {"message": "second"}, "final_output": null}',
            '{"done": true, "next_capability": null, "arguments": null, "final_output": null}',
        ]
        result = self.rotom.handle("echo hello", session_id="s1")
        self.assertEqual(self.llm_client.generate.call_count, 2)
        self.assertTrue(result.success)
        self.assertEqual(result.capability, "echo")
        self.assertEqual(result.output, "second")
        self.assertEqual(result.metadata.get("continuation_iteration"), 2)
        self.assertEqual(result.metadata.get("continuation_total_iterations"), 2)

    def test_two_step_echo_then_word_count_llm_decider(self):
        """Two steps: echo produces text, continuation says run word_count on that text; then done."""
        self.intent_classifier.classify.return_value = {
            "capability": "echo",
            "arguments": {"message": "one two three"},
        }
        self.llm_client.generate.side_effect = [
            '{"done": false, "next_capability": "word_count", "arguments": {"text": "one two three"}, "final_output": null}',
            '{"done": true, "next_capability": null, "arguments": null, "final_output": null}',
        ]
        result = self.rotom.handle("draft and count words", session_id="s1")
        self.assertEqual(self.llm_client.generate.call_count, 2)
        self.assertTrue(result.success)
        self.assertEqual(result.capability, "word_count")
        self.assertEqual(result.output, "3")
        self.assertEqual(result.metadata.get("continuation_total_iterations"), 2)

    def test_final_output_synthesis_llm_decider(self):
        """Single step; decider returns done=True with final_output; we surface synthesized reply."""
        self.llm_client.generate.return_value = (
            '{"done": true, "next_capability": null, "arguments": null, '
            '"final_output": "Here is a summary: hello"}'
        )
        result = self.rotom.handle("echo hello", session_id="s1")
        self.assertEqual(self.llm_client.generate.call_count, 1)
        self.assertEqual(result.output, "Here is a summary: hello")
        self.assertTrue(result.metadata.get("synthesized"))
        self.assertEqual(result.metadata.get("continuation_iteration"), 1)

    def test_three_step_then_done(self):
        """Three steps: echo -> echo -> word_count; decider says done after third."""
        self.intent_classifier.classify.return_value = {
            "capability": "echo",
            "arguments": {"message": "a b c"},
        }
        self.llm_client.generate.side_effect = [
            '{"done": false, "next_capability": "echo", "arguments": {"message": "x y z"}, "final_output": null}',
            '{"done": false, "next_capability": "word_count", "arguments": {"text": "x y z"}, "final_output": null}',
            '{"done": true, "next_capability": null, "arguments": null, "final_output": null}',
        ]
        result = self.rotom.handle("multi step", session_id="s1")
        self.assertEqual(self.llm_client.generate.call_count, 3)
        self.assertTrue(result.success)
        self.assertEqual(result.capability, "word_count")
        self.assertEqual(result.output, "3")
        self.assertEqual(result.metadata.get("continuation_total_iterations"), 3)
