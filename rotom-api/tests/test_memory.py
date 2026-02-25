"""
Unit tests for Phase 5 session memory (InMemorySessionMemory).

We test that:
  - Empty or missing session returns an empty context string.
  - Appending user + assistant entries and then get_context() returns a
    readable summary with "User: ..." and "Assistant ran ...; result: ...".
  - get_context(session_id, max_turns=N) only includes the last N turns.
  - Different session_ids have separate histories (no cross-talk).
"""

import unittest

from app.core.memory import InMemorySessionMemory


class TestInMemorySessionMemory(unittest.TestCase):
    def setUp(self):
        self.memory = InMemorySessionMemory(max_entries_per_session=20)

    def test_get_context_empty_returns_empty_string(self):
        """New or unknown session should return "" so the prompt has no context block."""
        self.assertEqual(self.memory.get_context("s1"), "")
        self.assertEqual(self.memory.get_context("s1", max_turns=5), "")

    def test_append_and_get_context_one_turn(self):
        """One user message + one assistant response should format as expected."""
        self.memory.append("s1", {"role": "user", "content": "hello"})
        self.memory.append("s1", {"role": "assistant", "capability": "echo", "output_summary": "hello"})
        ctx = self.memory.get_context("s1", max_turns=5)
        self.assertIn("User: hello", ctx)
        self.assertIn("Assistant ran echo; result: hello", ctx)

    def test_get_context_respects_max_turns(self):
        """Only the most recent max_turns turns should appear in the context string."""
        # 3 full turns = 6 entries (user, assistant, user, assistant, ...)
        for i in range(3):
            self.memory.append("s1", {"role": "user", "content": f"msg{i}"})
            self.memory.append("s1", {"role": "assistant", "capability": "echo", "output_summary": f"msg{i}"})
        # Ask for last 2 turns only → msg0 should be dropped
        ctx = self.memory.get_context("s1", max_turns=2)
        self.assertIn("msg1", ctx)
        self.assertIn("msg2", ctx)
        self.assertNotIn("msg0", ctx)

    def test_sessions_isolated(self):
        """Memory for session s1 must not leak into get_context(s2) and vice versa."""
        self.memory.append("s1", {"role": "user", "content": "from s1"})
        self.memory.append("s2", {"role": "user", "content": "from s2"})
        ctx1 = self.memory.get_context("s1")
        ctx2 = self.memory.get_context("s2")
        self.assertIn("from s1", ctx1)
        self.assertNotIn("from s2", ctx1)
        self.assertIn("from s2", ctx2)
        self.assertNotIn("from s1", ctx2)
