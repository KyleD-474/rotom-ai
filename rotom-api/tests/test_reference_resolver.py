"""
Unit tests for Phase 6: LLMReferenceResolver.

We mock BaseLLMClient.generate to return a fixed rewritten string and assert
that resolve(user_input, context) returns it. We also assert the prompt
passed to the LLM contains the context and user message.
"""

import unittest
# MagicMock: a fake object. When our code calls llm_client.generate(some_prompt),
# we want it to get back a string we choose—without calling the real OpenAI API.
# We set llm_client.generate.return_value = "echo hello", and then any call to
# .generate(...) returns "echo hello". We can also inspect .call_args to see
# what prompt was passed in.
from unittest.mock import MagicMock

from app.agents.reference_resolver import LLMReferenceResolver


class TestLLMReferenceResolver(unittest.TestCase):
    """
    We test the reference resolver by giving it a fake LLM client. So we never
    hit the real API; we just check that (1) the resolver returns what the
    "LLM" returned, and (2) the prompt the resolver built contains the right
    context and user message.
    """

    def setUp(self):
        # A fake LLM: we'll set .return_value on .generate so when the resolver
        # calls self.llm_client.generate(prompt), it gets our string.
        self.llm_client = MagicMock()
        self.resolver = LLMReferenceResolver(llm_client=self.llm_client)

    def test_resolve_returns_llm_output(self):
        """resolve() should return the stripped string returned by the LLM."""
        # When generate() is called, pretend the LLM returned "echo hello".
        self.llm_client.generate.return_value = "echo hello"
        # So when we call resolve, the resolver will build a prompt, call
        # llm_client.generate(prompt), get "echo hello", and return it.
        result = self.resolver.resolve("do that again", "User: echo hi\nAssistant: ran echo, result: hi")
        self.assertEqual(result, "echo hello")
        # And generate must have been called exactly once (one LLM call per resolve).
        self.llm_client.generate.assert_called_once()

    def test_resolve_prompt_contains_context_and_user_message(self):
        """The prompt sent to the LLM must include the context and user message."""
        self.llm_client.generate.return_value = "echo hello"
        self.resolver.resolve("do it again", "User: echo foo")
        # .call_args is the (args, kwargs) of the last call to .generate(...).
        # So call_args[0][0] is the first positional argument = the prompt string.
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
        # We should not call the LLM at all when there's no context (design choice).
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
