"""
Unit tests for Phase 7: Continuation decider (no-op and LLM).

NoOpContinuationDecider always returns done=True and no next step or final_output.
LLMContinuationDecider: we mock BaseLLMClient.generate to return JSON and assert
the parsed ContinuationResult has the expected fields.
"""

import unittest
# MagicMock: a fake object that records how it was called and can pretend to return
# any value you set. We use it so we never call a real LLM or network—we just
# say "when generate() is called, return this string" and then check our code
# parsed it correctly.
from unittest.mock import MagicMock

from app.agents.continuation import NoOpContinuationDecider, LLMContinuationDecider
from app.models.capability_result import CapabilityResult
from app.models.continuation_result import ContinuationResult


class TestNoOpContinuationDecider(unittest.TestCase):
    """
    No-op always returns done=True; no LLM call.

    unittest.TestCase: the base class for every test class. Each method whose
    name starts with test_ is run as a separate test. setUp runs before each test.
    """

    def setUp(self):
        # setUp: runs before every test_ method. We create one real NoOpContinuationDecider.
        # "No-op" = no operation: it does nothing, just returns a fixed answer.
        self.decider = NoOpContinuationDecider()

    def test_continue_returns_done_true(self):
        """continue_() should always return done=True and no next step or final_output."""
        # Build a fake "result" that looks like what a capability would return.
        # We're not running a real capability—we just need an object with the right shape.
        result = CapabilityResult(capability="echo", output="hello", success=True, metadata={})
        # Call the decider: "user said 'echo hello', we ran 'echo', here's the result."
        out = self.decider.continue_("echo hello", "echo", result)
        # The no-op should return a ContinuationResult (the structured answer).
        self.assertIsInstance(out, ContinuationResult)
        # Phase 7 no-op always says "we're done" (no next step).
        self.assertTrue(out.done)
        # It never asks to run another capability.
        self.assertIsNone(out.next_capability)
        self.assertIsNone(out.arguments)
        # It never provides a rewritten/synthesized reply.
        self.assertIsNone(out.final_output)


class TestLLMContinuationDecider(unittest.TestCase):
    """
    LLM decider parses JSON and returns ContinuationResult.

    Here we don't call a real LLM. We use MagicMock so that when our code
    calls llm_client.generate(prompt), it gets back whatever string we put
    in return_value. Then we check that the decider correctly parsed that
    string into a ContinuationResult.
    """

    def setUp(self):
        # MagicMock() creates a fake object. Any attribute you access (like .generate)
        # is also a MagicMock. So self.llm_client.generate is a fake method.
        self.llm_client = MagicMock()
        # We pass this fake LLM client into the decider. When the decider calls
        # self.llm_client.generate(prompt), it will get whatever we set below.
        self.decider = LLMContinuationDecider(llm_client=self.llm_client)

    def test_continue_parses_json_returns_continuation_result(self):
        """When the LLM returns valid JSON, we get a ContinuationResult with those fields."""
        # Tell the fake: "when generate() is called, return this JSON string."
        # So our code will never hit the real OpenAI API—it just gets this string.
        self.llm_client.generate.return_value = '{"done": true, "next_capability": null, "arguments": null, "final_output": null}'
        result = CapabilityResult(capability="echo", output="hi", success=True, metadata={})
        # The decider will build a prompt, call self.llm_client.generate(prompt),
        # get back the JSON string above, parse it, and return a ContinuationResult.
        out = self.decider.continue_("echo hi", "echo", result)
        self.assertIsInstance(out, ContinuationResult)
        self.assertTrue(out.done)
        self.assertIsNone(out.next_capability)
        self.assertIsNone(out.final_output)

    def test_continue_parses_done_false_and_next_capability(self):
        """LLM can return done=false with next_capability and arguments for Phase 8."""
        # Simulate the LLM saying "not done yet—run 'echo' with message 'again'."
        # Phase 8 would use this to loop and run another capability.
        self.llm_client.generate.return_value = '{"done": false, "next_capability": "echo", "arguments": {"message": "again"}, "final_output": null}'
        result = CapabilityResult(capability="echo", output="hi", success=True, metadata={})
        out = self.decider.continue_("do that again", "echo", result)
        self.assertFalse(out.done)
        self.assertEqual(out.next_capability, "echo")
        self.assertEqual(out.arguments, {"message": "again"})
        self.assertIsNone(out.final_output)

    def test_continue_invalid_json_returns_done_true(self):
        """When the LLM returns invalid JSON, we default to done=True so we don't loop forever."""
        # If the LLM misbehaves and returns garbage, our code should not crash—
        # it should fall back to "we're done" so we don't get stuck in a loop.
        self.llm_client.generate.return_value = "not valid json at all"
        result = CapabilityResult(capability="echo", output="hi", success=True, metadata={})
        out = self.decider.continue_("echo hi", "echo", result)
        self.assertIsInstance(out, ContinuationResult)
        self.assertTrue(out.done)
        self.assertIsNone(out.next_capability)
