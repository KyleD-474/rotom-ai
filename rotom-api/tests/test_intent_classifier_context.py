"""
Unit tests for Phase 5: context injection in the intent classifier prompt.

We don't call a real LLM here. We only check that _build_prompt() includes
a "Recent context (for reference):" block when context is non-empty, and that
it omits that block when context is None or empty. That way the LLM can
receive conversation history when we pass it from RotomCore.
"""

import unittest

from app.agents.intent.llm_intent_classifier import LLMIntentClassifier


class MockLLMClient:
    """
    A simple fake LLM client (not MagicMock—just a small class we wrote).
    Whenever generate(prompt) is called, we return the same valid JSON so that
    the classifier's .classify() method can run without error. We're not
    testing what the LLM would really say; we're only testing that _build_prompt
    produces a string that contains (or doesn't contain) "Recent context" and
    the user input. So we never need to hit the real API.
    """
    def generate(self, prompt: str) -> str:
        return '{"capability": "echo", "arguments": {"message": "hi"}}'


class TestLLMIntentClassifierContext(unittest.TestCase):
    """
    We test the *prompt* that the intent classifier builds—not the LLM's answer.
    We give it a MockLLMClient that always returns valid JSON, and we call
    _build_prompt(user_input, context) with different contexts. Then we assert
    the prompt string contains or doesn't contain "Recent context" and the
    user message. So we're checking: "when we have context, does it show up
    in the prompt? When we don't, is it omitted?"
    """

    def setUp(self):
        self.client = MockLLMClient()
        # tool_metadata: the list of capabilities the classifier knows about.
        # We pass a minimal one (just echo) so the classifier can build a valid prompt.
        self.classifier = LLMIntentClassifier(
            llm_client=self.client,
            tool_metadata=[{"name": "echo", "description": "Echo", "arguments": {"message": "desc"}}],
        )

    def test_build_prompt_without_context_has_no_recent_context_section(self):
        """When there's no session or no history, the prompt should not mention "Recent context"."""
        prompt = self.classifier._build_prompt("hello", context=None)
        self.assertNotIn("Recent context", prompt)
        self.assertIn("User input:", prompt)
        self.assertIn("hello", prompt)

    def test_build_prompt_with_empty_context_has_no_recent_context_section(self):
        """Empty string context should be treated like no context."""
        prompt = self.classifier._build_prompt("hello", context="")
        self.assertNotIn("Recent context", prompt)

    def test_build_prompt_with_context_includes_it(self):
        """When RotomCore passes a context string, it should appear in the prompt under "Recent context"."""
        context = "Previous: User said hi."
        prompt = self.classifier._build_prompt("echo that", context=context)
        self.assertIn("Recent context", prompt)
        self.assertIn("Previous: User said hi.", prompt)
        self.assertIn("User input:", prompt)
        self.assertIn("echo that", prompt)
