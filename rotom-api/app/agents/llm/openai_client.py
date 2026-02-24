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
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict JSON intent classifier."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0,
        )

        return response.choices[0].message.content.strip()