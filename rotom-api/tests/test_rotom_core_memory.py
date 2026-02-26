"""
Unit tests for Phase 5 and Phase 6: RotomCore's use of session memory and reference resolution.

We use a real CapabilityRegistry and a real capability (echo), but we mock
the session_store, session_memory, intent_classifier, and optionally reference_resolver.
That lets us verify:
  1. When session_id is set, RotomCore calls get_context(session_id, max_turns=5)
     and passes that context to the classifier (or to the resolver first in Phase 6).
  2. After handling the request, RotomCore calls append() twice (user entry,
     then assistant entry); the user entry is always the original user_input.
  3. When session_id is None, RotomCore does not call get_context or append.
  4. Phase 6: When reference_resolver is present and context is non-empty, we call
     the resolver and then classify(rewritten_message, context=None); memory still
     stores the original user message.
No real LLM or memory backend is used—only mocks.
"""

import unittest
from unittest.mock import MagicMock

from app.agents.rotom_core import RotomCore
from app.capabilities.registry import CapabilityRegistry  # includes EchoCapability


class TestRotomCoreMemory(unittest.TestCase):
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
        # No reference_resolver in default setUp so we test Phase 5 behavior:
        # classifier receives context when session has history.
        self.rotom = RotomCore(
            intent_classifier=self.intent_classifier,
            registry=self.registry,
            session_store=self.session_store,
            session_memory=self.session_memory,
        )

    def test_handle_with_session_id_calls_get_context_and_classify_with_context(self):
        """With a session_id and no resolver, RotomCore passes context to the classifier."""
        self.session_memory.get_context.return_value = "User: previous message"
        result = self.rotom.handle("echo hello", session_id="s1")
        self.session_memory.get_context.assert_called_once_with("s1", max_turns=5)
        self.intent_classifier.classify.assert_called_once_with(
            "echo hello",
            context="User: previous message",
        )
        self.assertTrue(result.success)
        self.assertEqual(result.capability, "echo")

    def test_handle_with_resolver_rewrites_then_classifies_with_no_context(self):
        """Phase 6: With session_id, context, and reference_resolver, classify gets rewritten message and context=None."""
        self.session_memory.get_context.return_value = "User: echo hi\nAssistant: ran echo, result: hi"
        resolver = MagicMock()
        resolver.resolve.return_value = "echo hello"
        rotom_with_resolver = RotomCore(
            intent_classifier=self.intent_classifier,
            registry=self.registry,
            session_store=self.session_store,
            session_memory=self.session_memory,
            reference_resolver=resolver,
        )
        result = rotom_with_resolver.handle("do that again", session_id="s1")
        resolver.resolve.assert_called_once_with(
            "do that again",
            "User: echo hi\nAssistant: ran echo, result: hi",
        )
        self.intent_classifier.classify.assert_called_once_with("echo hello", context=None)
        self.assertTrue(result.success)

    def test_handle_with_resolver_appends_original_user_message(self):
        """Phase 6: Memory must store the original user message, not the rewritten one."""
        self.session_memory.get_context.return_value = "User: echo hi"
        resolver = MagicMock()
        resolver.resolve.return_value = "echo hello"
        rotom_with_resolver = RotomCore(
            intent_classifier=self.intent_classifier,
            registry=self.registry,
            session_store=self.session_store,
            session_memory=self.session_memory,
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
        """Stateless requests (no session_id) must not touch memory—same behavior as pre-Phase-5."""
        self.rotom.handle("echo hello", session_id=None)
        self.session_memory.get_context.assert_not_called()
        self.session_memory.append.assert_not_called()
        self.intent_classifier.classify.assert_called_once_with("echo hello", context=None)
