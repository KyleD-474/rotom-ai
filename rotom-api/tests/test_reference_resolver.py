"""
Unit tests for Phase 6: LLMReferenceResolver.

We mock BaseLLMClient.generate to return a fixed rewritten string and assert
that resolve(user_input, context) returns it. We also assert the prompt
passed to the LLM contains the context and user message.
"""

import unittest
from unittest.mock import MagicMock

from app.agents.reference_resolver import LLMReferenceResolver


class TestLLMReferenceResolver(unittest.TestCase):
    def setUp(self):
        self.llm_client = MagicMock()
        self.resolver = LLMReferenceResolver(llm_client=self.llm_client)

    def test_resolve_returns_llm_output(self):
        """resolve() should return the stripped string returned by the LLM."""
        self.llm_client.generate.return_value = "echo hello"
        result = self.resolver.resolve("do that again", "User: echo hi\nAssistant: ran echo, result: hi")
        self.assertEqual(result, "echo hello")
        self.llm_client.generate.assert_called_once()

    def test_resolve_prompt_contains_context_and_user_message(self):
        """The prompt sent to the LLM must include the context and user message."""
        self.llm_client.generate.return_value = "echo hello"
        self.resolver.resolve("do it again", "User: echo foo")
        call_args = self.llm_client.generate.call_args
        prompt = call_args[0][0]
        self.assertIn("User: echo foo", prompt)
        self.assertIn("do it again", prompt)
        self.assertIn("Recent context", prompt)
        self.assertIn("User message:", prompt)

    def test_resolve_empty_context_returns_user_input_unchanged(self):
        """When context is empty or whitespace, return user_input without calling the LLM."""
        result = self.resolver.resolve("hello", "")
        self.assertEqual(result, "hello")
        self.llm_client.generate.assert_not_called()

        self.llm_client.generate.reset_mock()
        result = self.resolver.resolve("hello", "   ")
        self.assertEqual(result, "hello")
        self.llm_client.generate.assert_not_called()

    def test_resolve_strips_llm_output(self):
        """Whitespace around the LLM reply should be stripped."""
        self.llm_client.generate.return_value = "  echo hello  \n"
        result = self.resolver.resolve("that", "User: echo hi")
        self.assertEqual(result, "echo hello")
