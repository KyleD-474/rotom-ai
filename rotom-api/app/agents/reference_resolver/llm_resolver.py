"""
llm_resolver.py — Phase 6: LLM-backed reference resolver

Given (user_input, context), this implementation asks the LLM to rewrite the
user message so that references like "that", "it", "again" are resolved from
the recent context. It uses the same BaseLLMClient abstraction as the intent
classifier so we can test with a mock and swap providers in one place.
"""

from app.agents.reference_resolver.base_reference_resolver import BaseReferenceResolver
from app.agents.llm.base_llm_client import BaseLLMClient
from app.core.logger import get_logger

logger = get_logger(__name__, layer="agent", component="reference_resolver")


class LLMReferenceResolver(BaseReferenceResolver):
    """
    Calls the LLM with a short prompt: context + user message, instruct it to
    output only the rewritten message (no explanation, no JSON). Strip and return.
    """

    def __init__(self, llm_client: BaseLLMClient):
        self.llm_client = llm_client

    def resolve(self, user_input: str, context: str) -> str:
        """
        If context is empty or whitespace, return user_input unchanged (defensive—
        RotomCore normally only calls us when context exists, but this avoids LLM
        calls with empty context). Otherwise build a prompt, call the LLM, and
        return the stripped reply (the rewritten message only, no JSON or explanation).
        """
        if not context or not context.strip():
            return user_input.strip() if user_input else user_input

        prompt = self._build_prompt(user_input, context.strip())
        raw = self.llm_client.generate(prompt)
        return raw.strip() if raw else user_input

    def _build_prompt(self, user_input: str, context: str) -> str:
        """
        Build a single prompt that asks the LLM to output only the rewritten
        message in the form the user would have typed—e.g. if they said "do that
        again" and the prior user message was "echo Phase 6 test", output
        "echo Phase 6 test", not a description like "run the echo command again".
        """
        return f"""You are a reference resolver. Given the recent conversation context and the user's message, output the EXACT message the user would have typed to mean the same thing—resolve references like "that", "it", "again" by substituting the prior user message or the action they refer to.

CRITICAL: Output only the resolved message AS THE USER WOULD HAVE TYPED IT. Do NOT output a description or instruction (e.g. do NOT output "run the echo command again" or "repeat the previous echo"). If the user said "do that again" and the previous user message was "echo hello", output exactly: echo hello

Recent context:
{context}

User message:
{user_input}

Resolved message (exactly what the user would have typed, nothing else):"""
