"""
backend/evaluation/judge.py — LLM Judge interface, client implementations, and budget tracking.

Rules:
- Opt-in judge (judge=true).
- Metrics: faithfulness (supported/claims) and answer_relevance (1.0 / 0.5 / 0.0).
- JudgeClient interface, temperature 0, strict JSON output.
- Answer and chunks passed as untrusted data in XML wrappers.
- Judge model recorded; labeled "LLM-judged, uncalibrated" in reports.
- Live runs require an explicit max_llm_calls budget counting generation AND judge calls.
  Exceeding budget cleanly stops the run (status failed, error "budget").
"""

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BudgetExceededException(Exception):
    """Raised when total LLM calls (generation + judge) exceed max_llm_calls."""
    pass


class CallBudgetTracker:
    """Tracks LLM call budget across generation and judge operations."""

    def __init__(self, max_calls: Optional[int] = None):
        self.max_calls = max_calls
        self.generation_calls = 0
        self.judge_calls = 0

    @property
    def total_calls(self) -> int:
        return self.generation_calls + self.judge_calls

    def record_generation_call(self) -> None:
        if self.max_calls is not None and self.total_calls >= self.max_calls:
            raise BudgetExceededException("budget")
        self.generation_calls += 1

    def record_judge_call(self) -> None:
        if self.max_calls is not None and self.total_calls >= self.max_calls:
            raise BudgetExceededException("budget")
        self.judge_calls += 1


class JudgeClient(ABC):
    """Abstract interface for LLM Judge."""

    @abstractmethod
    def evaluate_faithfulness(
        self, question: str, answer: str, context_chunks: List[str]
    ) -> Dict[str, Any]:
        """
        Extract claims from answer and label each supported/unsupported given context chunks.
        Returns {"score": float, "claims": List[Dict[str, Any]], "model": str}
        """
        pass

    @abstractmethod
    def evaluate_answer_relevance(
        self, question: str, answer: str
    ) -> Dict[str, Any]:
        """
        Evaluate whether answer addresses question.
        Returns {"score": float, "verdict": str, "model": str}
        """
        pass


class FakeJudgeClient(JudgeClient):
    """Deterministic fake judge for testing and offline runs."""

    def __init__(
        self,
        faithfulness_score: float = 1.0,
        relevance_verdict: str = "addresses",
        model_name: str = "fake-judge-v1",
        budget_tracker: Optional[CallBudgetTracker] = None,
    ):
        self.faithfulness_score = faithfulness_score
        self.relevance_verdict = relevance_verdict
        self.model_name = model_name
        self.budget_tracker = budget_tracker

    def evaluate_faithfulness(
        self, question: str, answer: str, context_chunks: List[str]
    ) -> Dict[str, Any]:
        if self.budget_tracker:
            self.budget_tracker.record_judge_call()

        return {
            "score": self.faithfulness_score,
            "claims": [
                {"claim": "Sample claim from answer", "supported": self.faithfulness_score >= 0.5}
            ],
            "model": self.model_name,
            "label": "LLM-judged, uncalibrated",
        }

    def evaluate_answer_relevance(
        self, question: str, answer: str
    ) -> Dict[str, Any]:
        if self.budget_tracker:
            self.budget_tracker.record_judge_call()

        verdict_map = {"addresses": 1.0, "partially": 0.5, "does_not_address": 0.0}
        score = verdict_map.get(self.relevance_verdict, 1.0)
        return {
            "score": score,
            "verdict": self.relevance_verdict,
            "model": self.model_name,
            "label": "LLM-judged, uncalibrated",
        }


class GeminiJudgeClient(JudgeClient):
    """Live Gemini-based JudgeClient using temperature 0 and strict JSON."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.0-flash",
        budget_tracker: Optional[CallBudgetTracker] = None,
    ):
        import os
        from google import genai
        from google.genai import types

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.budget_tracker = budget_tracker
        self.client = genai.Client(api_key=self.api_key)

    def evaluate_faithfulness(
        self, question: str, answer: str, context_chunks: List[str]
    ) -> Dict[str, Any]:
        if self.budget_tracker:
            self.budget_tracker.record_judge_call()

        chunks_xml = "\n".join(
            f"<context_chunk index='{i}'>{c}</context_chunk>"
            for i, c in enumerate(context_chunks, start=1)
        )

        prompt = (
            "You are an impartial evaluation judge. You will evaluate the faithfulness of an answer given context chunks.\n"
            "UNTRUSTED CONTEXT CHUNKS:\n"
            f"{chunks_xml}\n\n"
            "UNTRUSTED GENERATED ANSWER:\n"
            f"<answer>{answer}</answer>\n\n"
            "Task:\n"
            "1. Break the answer down into atomic factual claims.\n"
            "2. For each claim, determine if it is directly supported by the context chunks (true or false).\n"
            "3. Output strictly valid JSON with keys: 'claims' (list of {'claim': str, 'supported': bool}) and 'score' (supported_claims / total_claims).\n"
            "If there are zero factual claims, score is 1.0."
        )

        from google.genai import types
        config = types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
        )

        resp = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )

        try:
            parsed = json.loads(resp.text)
            score = float(parsed.get("score", 0.0))
            claims = parsed.get("claims", [])
        except Exception:
            score = 0.0
            claims = []

        return {
            "score": round(score, 4),
            "claims": claims,
            "model": self.model_name,
            "label": "LLM-judged, uncalibrated",
        }

    def evaluate_answer_relevance(
        self, question: str, answer: str
    ) -> Dict[str, Any]:
        if self.budget_tracker:
            self.budget_tracker.record_judge_call()

        prompt = (
            "You are an impartial evaluation judge. You will evaluate how well a generated answer addresses the question asked.\n"
            f"QUESTION:\n<question>{question}</question>\n\n"
            f"ANSWER:\n<answer>{answer}</answer>\n\n"
            "Task:\n"
            "Categorize how well the answer addresses the question into one of: 'addresses', 'partially', or 'does_not_address'.\n"
            "Output strictly valid JSON with keys: 'verdict' and 'explanation'."
        )

        from google.genai import types
        config = types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
        )

        resp = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )

        try:
            parsed = json.loads(resp.text)
            verdict = parsed.get("verdict", "does_not_address")
        except Exception:
            verdict = "does_not_address"

        verdict_map = {"addresses": 1.0, "partially": 0.5, "does_not_address": 0.0}
        score = verdict_map.get(verdict, 0.0)

        return {
            "score": score,
            "verdict": verdict,
            "model": self.model_name,
            "label": "LLM-judged, uncalibrated",
        }

