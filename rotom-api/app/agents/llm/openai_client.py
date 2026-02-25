"""
openai_client.py — OpenAI implementation of the LLM client

Used by the intent classifier to call the OpenAI API. Reads OPENAI_API_KEY
and OPENAI_MODEL from the environment. The system message tells the model to
act as a strict JSON intent classifier so we get parseable capability +
arguments back. Temperature 0 keeps responses deterministic.
"""

import os
from openai import OpenAI

from app.agents.llm.base_llm_client import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate(self, prompt: str) -> str:
        """Call the OpenAI chat API with the intent-classification prompt; return the assistant message content."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a strict JSON intent classifier."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()