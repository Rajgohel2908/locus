"""
generation/llm.py — LLM client interface and Google Gen AI implementation.

Uses the current google-genai SDK (not the deprecated google-generativeai).
Config-driven (no hardcoded model names in code), with exponential backoff retries.
Production client contains NO demo-specific or keyword-based canned answers.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
import time
import logging
import config

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when the LLM service fails permanently after retries."""
    pass


class LLMClient(ABC):
    """Abstract interface for LLM text generation."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate response text for the provided prompt."""
        pass


class GeminiLLMClient(LLMClient):
    """
    Google GenAI client using the official google-genai SDK.
    Configured via environment variables with exponential backoff on transient errors.
    Contains NO fallback mock behavior or keyword canned answers.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
    ):
        self.api_key = api_key if api_key is not None else config.GEMINI_API_KEY
        self.provider = config.LLM_PROVIDER
        self.model_name = model_name or config.GEMINI_MODEL
        self.timeout = timeout or config.LLM_TIMEOUT
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self._client = None
        self.is_mock = False

    def _get_client(self):
        if self._client is None:
            from google import genai
            timeout_ms = int(self.timeout * 1000) if self.timeout else None
            http_options = {"timeout": timeout_ms} if timeout_ms else None
            self._client = genai.Client(
                api_key=self.api_key,
                http_options=http_options,
            )
        return self._client

    def generate(self, prompt: str) -> str:
        # Check if real API key is configured
        if not self.api_key or self.api_key.strip() in ("", "your_gemini_api_key_here"):
            raise LLMError(
                "GEMINI_API_KEY is not configured or empty. "
                "Please configure a valid GEMINI_API_KEY or set LLM_PROVIDER=mock."
            )

        client = self._get_client()
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
                if response and hasattr(response, "text") and response.text:
                    return response.text
                return ""
            except Exception as e:
                last_exception = e
                err_str = str(e).lower()
                # Check for rate-limit, quota, transient network timeouts, or 5xx server errors
                is_transient = any(
                    x in err_str for x in ["429", "rate", "quota", "500", "503", "504", "server", "unavailable", "timeout", "timed out", "connect", "connection", "handshake"]
                )
                if attempt < self.max_retries and is_transient:
                    backoff = self.initial_backoff * (2 ** attempt)
                    logger.warning(
                        f"LLM request failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}. Retrying in {backoff:.1f}s..."
                    )
                    time.sleep(backoff)
                else:
                    if not is_transient:
                        logger.error(f"Non-retriable LLM error: {e}")
                        break

        raise LLMError(f"LLM generation failed after {self.max_retries + 1} attempts: {last_exception}")


class FakeLLMClient(LLMClient):
    """
    In-memory mock LLM client for deterministic testing without external API calls.
    Supports canned responses, simulated transient retries, and simulated permanent failure.
    """

    def __init__(
        self,
        response: str = "This is a factual statement [1].",
        fail_times: int = 0,
        always_fail: bool = False,
        is_mock: bool = False,
    ):
        self.response = response
        self.fail_times = fail_times
        self.always_fail = always_fail
        self.call_count = 0
        self.recorded_prompts: List[str] = []
        self.provider = "mock"
        self.model_name = "mock"
        self.is_mock = is_mock

    def generate(self, prompt: str) -> str:
        self.call_count += 1
        self.recorded_prompts.append(prompt)

        if self.always_fail or self.call_count <= self.fail_times:
            raise LLMError("Simulated LLM service failure")

        if callable(self.response):
            return self.response(prompt)
        return self.response


# Global client instance
_llm_client_instance: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Return the global LLM client singleton according to LLM_PROVIDER configuration."""
    global _llm_client_instance
    if _llm_client_instance is None:
        if getattr(config, "LLM_PROVIDER", "gemini") == "mock":
            from generation.mock_llm import MockLLMClient
            _llm_client_instance = MockLLMClient()
        else:
            _llm_client_instance = GeminiLLMClient()
    return _llm_client_instance


def set_llm_client(client: LLMClient) -> None:
    """Override the global LLM client (used in tests to inject FakeLLMClient or MockLLMClient)."""
    global _llm_client_instance
    _llm_client_instance = client
