"""
generation/mock_llm.py — Generic Mock LLM client for testing and offline development.

Used only when LLM_PROVIDER=mock is set explicitly or injected in tests.
Echoes the first chunk text with its citation in a generic, non-canned manner.
Contains NO demo-specific or keyword-based canned answers.
"""

import re
from typing import Optional
from generation.llm import LLMClient


class MockLLMClient(LLMClient):
    """
    Generic mock LLM for testing and offline development.
    Echoes the first prompt chunk text with its citation.
    Always includes provider, model, and is_mock=True metadata.
    """

    def __init__(self, provider: str = "mock", model_name: str = "mock"):
        self.provider = provider
        self.model_name = model_name
        self.is_mock = True

    def generate(self, prompt: str) -> str:
        chunks = re.findall(r'<chunk id="(\d+)"[^>]*>(.*?)</chunk>', prompt, re.DOTALL)
        if not chunks:
            return "[MOCK] Information not available in context."

        cid, content = chunks[0]
        # Extract the first non-empty content sentence or line
        lines = [line.strip() for line in content.strip().split("\n") if line.strip()]
        first_line = lines[0] if lines else "Relevant context"
        if first_line.endswith("."):
            first_line = first_line[:-1]

        # Generic factual response echoing context with citation
        return f"[MOCK] Based on the provided context, {first_line} [{cid}]."
