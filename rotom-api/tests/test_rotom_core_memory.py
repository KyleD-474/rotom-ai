"""
Unit tests for Phase 5, Phase 6, Phase 7, and Phase 8: RotomCore's use of session memory,
reference resolution, continuation, and the iterative loop.

We use a real CapabilityRegistry and a real capability (echo), but we mock
the session_store, session_memory, intent_classifier, and optionally reference_resolver
and continuation_decider. That lets us verify:
  1. When session_id is set, RotomCore calls get_context(session_id, max_turns=5)
     and passes that context to the classifier (or to the resolver first in Phase 6).
  2. After handling the request, RotomCore calls append() twice (user entry,
     then assistant entry); the user entry is always the original user_input.
  3. When session_id is None, RotomCore does not call get_context or append.
  4. Phase 6: When reference_resolver is present and context is non-empty, we call
     the resolver and then classify(rewritten_message, context=None); memory still
     stores the original user message.
  5. Phase 7: When continuation_decider is present, we call continue_() after execution
     and use the return value; Phase 8 loops when done=False with next_capability/arguments.
No real LLM or memory backend is used—only mocks.
"""

import unittest
# MagicMock: a fake object that records every call (method name, arguments). We can
# set .return_value so when code calls that method it gets our fake value. We use
# it to replace session_store, session_memory, intent_classifier, etc., so we
# never touch a real database or LLM—we just check "did RotomCore call this with
# the right arguments?"
from unittest.mock import MagicMock

from app.agents.rotom_core import RotomCore, MAX_CONTINUATION_ITERATIONS
from app.capabilities.registry import CapabilityRegistry  # includes EchoCapability


class TestRotomCoreMemory(unittest.TestCase):
    """
    We test RotomCore by giving it mostly fake dependencies (mocks) and one real
    registry with the real echo capability. So when RotomCore runs, it actually
    executes the echo capability, but the "intent" comes from our mock—we tell
    the mock to return {"capability": "echo", "arguments": {"message": "hello"}}
    so we don't need a real LLM. We then check that RotomCore called the memory
    and classifier the way we expect.
    """

    def setUp(self):
        # Real registry and real echo capability—so we can test the full path
        # from "classifier says echo" to "echo runs and returns output."
        self.registry = CapabilityRegistry()
        # Fake session store: when RotomCore calls .get(session_id), return a fake
        # object that has session_id="s1". We never really store anything.
        self.session_store = MagicMock()
        self.session_store.get.return_value = MagicMock(session_id="s1")
        # Fake memory: .get_context() returns "" by default (no prior conversation).
        # We can override this in individual tests to simulate "there was prior context."
        self.session_memory = MagicMock()
        self.session_memory.get_context.return_value = ""
        # Fake intent classifier: when RotomCore calls .classify(user_input, context),
        # we want it to get back "run echo with message hello" so the rest of the
        # pipeline runs. No real LLM is called.
        self.intent_classifier = MagicMock()
        self.intent_classifier.classify.return_value = {
            "capability": "echo",
            "arguments": {"message": "hello"},
        }
        # We don't inject reference_resolver or continuation_decider here, so we
        # test the "Phase 5 style" path: classifier gets context when we set it.
        self.rotom = RotomCore(
            intent_classifier=self.intent_classifier,
            registry=self.registry,
            session_store=self.session_store,
            session_memory=self.session_memory,
        )

    def test_handle_with_session_id_calls_get_context_and_classify_with_context(self):
        """With a session_id and no resolver, RotomCore passes context to the classifier."""
        # Simulate "there was a previous message in this session."
        self.session_memory.get_context.return_value = "User: previous message"
        result = self.rotom.handle("echo hello", session_id="s1")
        # RotomCore should have asked memory for context exactly once, for session "s1", max 5 turns.
        self.session_memory.get_context.assert_called_once_with("s1", max_turns=5)
        # And it should have called the classifier with the user message and that context.
        self.intent_classifier.classify.assert_called_once_with(
            "echo hello",
            context="User: previous message",
        )
        # The real echo capability ran (because classifier returned echo/hello), so we get success.
        self.assertTrue(result.success)
        self.assertEqual(result.capability, "echo")

    def test_handle_with_resolver_rewrites_then_classifies_with_no_context(self):
        """Phase 6: With session_id, context, and reference_resolver, classify gets rewritten message and context=None."""
        self.session_memory.get_context.return_value = "User: echo hi\nAssistant: ran echo, result: hi"
        # Fake resolver: when RotomCore calls resolve("do that again", context), return "echo hello".
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
        # RotomCore should have called the resolver with the raw input and context.
        resolver.resolve.assert_called_once_with(
            "do that again",
            "User: echo hi\nAssistant: ran echo, result: hi",
        )
        # Then the classifier gets the *rewritten* message and no context (Phase 6 design).
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
        # append() was called; call_args_list is a list of (args, kwargs) for each call.
        calls = self.session_memory.append.call_args_list
        # First append is the user turn: we must store "do that again", not "echo hello".
        self.assertEqual(calls[0][0][1], {"role": "user", "content": "do that again"})

    def test_handle_with_session_id_appends_user_and_assistant_entries(self):
        """After execution, RotomCore should append the user message and a short assistant summary."""
        self.rotom.handle("echo hello", session_id="s1")
        # Two appends: one for the user message, one for the assistant summary.
        self.assertEqual(self.session_memory.append.call_count, 2)
        calls = self.session_memory.append.call_args_list
        # First call: session_id "s1", and the dict is the user entry.
        self.assertEqual(calls[0][0][0], "s1")
        self.assertEqual(calls[0][0][1], {"role": "user", "content": "echo hello"})
        # Second call: assistant entry with capability name and output summary.
        self.assertEqual(calls[1][0][0], "s1")
        self.assertEqual(calls[1][0][1]["role"], "assistant")
        self.assertEqual(calls[1][0][1]["capability"], "echo")
        self.assertEqual(calls[1][0][1]["output_summary"], "hello")

    def test_handle_without_session_id_does_not_call_get_context_or_append(self):
        """Stateless requests (no session_id) must not touch memory—same behavior as pre-Phase-5."""
        self.rotom.handle("echo hello", session_id=None)
        # With no session, we must not read or write memory.
        self.session_memory.get_context.assert_not_called()
        self.session_memory.append.assert_not_called()
        self.intent_classifier.classify.assert_called_once_with("echo hello", context=None)

    def test_handle_with_continuation_decider_calls_continue_but_returns_capability_result(self):
        """Phase 7: When continuation_decider is present, we call continue_() after execution but still return the same result."""
        # Fake continuation decider. We don't care what it returns for this test;
        # we just need it to have a .continue_() method that was called.
        continuation_decider = MagicMock()
        continuation_decider.continue_.return_value = MagicMock(done=True, next_capability=None, arguments=None, final_output=None)
        rotom_with_continuation = RotomCore(
            intent_classifier=self.intent_classifier,
            registry=self.registry,
            session_store=self.session_store,
            session_memory=self.session_memory,
            continuation_decider=continuation_decider,
        )
        result = rotom_with_continuation.handle("echo hello", session_id="s1")
        # RotomCore must have called the decider exactly once (after running the capability).
        continuation_decider.continue_.assert_called_once()
        # Check it was called with the right arguments: user message, capability name, result.
        call_args = continuation_decider.continue_.call_args[0]
        self.assertEqual(call_args[0], "echo hello")
        self.assertEqual(call_args[1], "echo")
        self.assertEqual(call_args[2].output, "hello")
        # Phase 7/8: with done=True we return the capability result (no loop).
        self.assertTrue(result.success)
        self.assertEqual(result.capability, "echo")
        self.assertEqual(result.output, "hello")
        # Memory append: user + assistant once.
        self.assertEqual(self.session_memory.append.call_count, 2)

    # --- Phase 8: Iterative loop tests ---

    def test_handle_phase8_loop_when_continuation_says_not_done(self):
        """Phase 8: When continuation returns done=False with next_capability/arguments, we run that capability and loop until done=True."""
        continuation_decider = MagicMock()
        # First call (after first echo): say "not done, run echo again with message 'second'."
        # Second call (after second echo): say "done."
        continuation_decider.continue_.side_effect = [
            MagicMock(done=False, next_capability="echo", arguments={"message": "second"}, final_output=None),
            MagicMock(done=True, next_capability=None, arguments=None, final_output=None),
        ]
        rotom = RotomCore(
            intent_classifier=self.intent_classifier,
            registry=self.registry,
            session_store=self.session_store,
            session_memory=self.session_memory,
            continuation_decider=continuation_decider,
        )
        result = rotom.handle("echo hello", session_id="s1")
        # Decider called twice: after first run and after second run.
        self.assertEqual(continuation_decider.continue_.call_count, 2)
        # First call: user_input, "echo", result with output "hello".
        self.assertEqual(continuation_decider.continue_.call_args_list[0][0][2].output, "hello")
        # Second call: user_input, "echo", result with output "second".
        self.assertEqual(continuation_decider.continue_.call_args_list[1][0][2].output, "second")
        # We return the last capability result (second run).
        self.assertEqual(result.output, "second")
        self.assertEqual(result.capability, "echo")
        # Memory: user once, then assistant entry per step (2 steps -> 2 assistant entries).
        self.assertEqual(self.session_memory.append.call_count, 1 + 2)

    def test_handle_phase8_max_iteration_guard(self):
        """Phase 8: When continuation always returns done=False, we stop after MAX_CONTINUATION_ITERATIONS and return last result."""
        continuation_decider = MagicMock()
        continuation_decider.continue_.return_value = MagicMock(
            done=False, next_capability="echo", arguments={"message": "again"}, final_output=None
        )
        rotom = RotomCore(
            intent_classifier=self.intent_classifier,
            registry=self.registry,
            session_store=self.session_store,
            session_memory=self.session_memory,
            continuation_decider=continuation_decider,
        )
        result = rotom.handle("echo hello", session_id="s1")
        # Should have called continue_ once per iteration, and we stop at max iterations.
        self.assertEqual(continuation_decider.continue_.call_count, MAX_CONTINUATION_ITERATIONS)
        # Last result should be from the final echo run (output "again").
        self.assertEqual(result.output, "again")
        self.assertEqual(result.capability, "echo")

    def test_handle_phase8_invalid_next_step_returns_last_result(self):
        """Phase 8: When continuation returns done=False but next_capability is not in registry, we stop and return last result."""
        continuation_decider = MagicMock()
        continuation_decider.continue_.return_value = MagicMock(
            done=False, next_capability="nonexistent_cap", arguments={"x": "y"}, final_output=None
        )
        rotom = RotomCore(
            intent_classifier=self.intent_classifier,
            registry=self.registry,
            session_store=self.session_store,
            session_memory=self.session_memory,
            continuation_decider=continuation_decider,
        )
        result = rotom.handle("echo hello", session_id="s1")
        # Decider called once; we try to resolve next_capability, fail, and return first result.
        self.assertEqual(continuation_decider.continue_.call_count, 1)
        self.assertEqual(result.output, "hello")
        self.assertEqual(result.capability, "echo")

    def test_handle_phase8_missing_next_capability_or_arguments_stops_loop(self):
        """Phase 8: When continuation returns done=False but next_capability or arguments missing, we stop and return last result."""
        continuation_decider = MagicMock()
        continuation_decider.continue_.return_value = MagicMock(
            done=False, next_capability=None, arguments=None, final_output=None
        )
        rotom = RotomCore(
            intent_classifier=self.intent_classifier,
            registry=self.registry,
            session_store=self.session_store,
            session_memory=self.session_memory,
            continuation_decider=continuation_decider,
        )
        result = rotom.handle("echo hello", session_id="s1")
        self.assertEqual(continuation_decider.continue_.call_count, 1)
        self.assertEqual(result.output, "hello")
        self.assertEqual(result.capability, "echo")

    def test_handle_phase8_final_output_surfaces_synthesized_reply(self):
        """Phase 8: When continuation returns done=True with final_output set, we return a result with that output and synthesized metadata."""
        continuation_decider = MagicMock()
        continuation_decider.continue_.return_value = MagicMock(
            done=True, next_capability=None, arguments=None, final_output="Here is a summary: hello"
        )
        rotom = RotomCore(
            intent_classifier=self.intent_classifier,
            registry=self.registry,
            session_store=self.session_store,
            session_memory=self.session_memory,
            continuation_decider=continuation_decider,
        )
        result = rotom.handle("echo hello", session_id="s1")
        self.assertEqual(result.output, "Here is a summary: hello")
        self.assertTrue(result.metadata.get("synthesized"))
        self.assertEqual(result.capability, "echo")
