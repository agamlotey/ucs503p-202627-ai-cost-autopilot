"""
autopilot.py
-------------
The "brain" of the gateway. For every incoming message it decides:

  1. CACHE HIT   -> return the saved answer, cost = $0, no call to the LLM.
  2. TRIM        -> the message is big/boilerplate-heavy, compress it, then call the LLM.
  3. PASSTHROUGH -> message is small/normal, send it straight to the LLM.

Drop this file in your `autopilot/` folder. It has no hard dependency on
OpenAI's embeddings API — it will use them if OPENAI_API_KEY is set
(better semantic matching), and otherwise falls back to a pure-Python
similarity check (no external calls, no cost).

Usage:
    from autopilot import Autopilot

    pilot = Autopilot()
    result = pilot.handle(user_message, call_llm_fn=my_llm_call)
    print(result["answer"], result["route"], result["cost_estimate"])
"""

import difflib
import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Optional


class Trimmer:
    """Compress large or repetitive input while preserving important sections."""

    PROTECTED_PATTERNS = [
        r"```.*?```",
        r"<instructions>.*?</instructions>",
        r"<task>.*?</task>",
    ]

    def __init__(self, size_threshold_chars: int = 4000):
        self.size_threshold_chars = size_threshold_chars

    def should_trim(self, text: str) -> bool:
        return len(text) >= self.size_threshold_chars

    def trim(self, text: str) -> str:
        protected = []

        def _stash(match):
            protected.append(match.group(0))
            return f"__PROTECTED_{len(protected) - 1}__"

        combined_pattern = "|".join(self.PROTECTED_PATTERNS)
        stashed_text = re.sub(combined_pattern, _stash, text, flags=re.DOTALL)
        stashed_text = re.sub(r"<[^>]+>", " ", stashed_text)
        stashed_text = re.sub(r"[ \t]+", " ", stashed_text)
        stashed_text = re.sub(r"\n{3,}", "\n\n", stashed_text)

        seen = set()
        deduped_lines = []
        for line in stashed_text.split("\n"):
            key = line.strip()
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            deduped_lines.append(line)
        result = "\n".join(deduped_lines).strip()

        for i, block in enumerate(protected):
            result = result.replace(f"__PROTECTED_{i}__", block)

        return result


class SecretsFilter:
    """Conservatively detect common secrets and personally identifying data."""

    PATTERNS = [
        r"sk-[A-Za-z0-9]{20,}",
        r"AIza[0-9A-Za-z\-_]{35}",
        r"ghp_[A-Za-z0-9]{36}",
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
        r"(?i)\b(password|passwd|pwd|api[_-]?key|secret|token)\s*[:=]\s*\S+",
        r"\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b",
        r"\b\d{3}-\d{2}-\d{4}\b",
    ]

    def __init__(self):
        self._compiled = [re.compile(pattern) for pattern in self.PATTERNS]

    def contains_secret(self, text: str) -> bool:
        return any(pattern.search(text) for pattern in self._compiled)


@dataclass
class CacheEntry:
    question: str
    answer: str
    embedding: Optional[list] = None
    created_at: float = field(default_factory=time.time)


class SemanticCache:
    """In-memory semantic cache with an optional OpenAI embedding backend."""

    def __init__(self, similarity_threshold: float = 0.90):
        self.entries: list[CacheEntry] = []
        self.similarity_threshold = similarity_threshold
        self._openai_client = self._init_openai_client()

    def _init_openai_client(self):
        if not os.environ.get("OPENAI_API_KEY"):
            return None
        try:
            from openai import OpenAI
            return OpenAI()
        except ImportError:
            return None

    def _embed(self, text: str) -> Optional[list]:
        if not self._openai_client:
            return None
        response = self._openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return response.data[0].embedding

    @staticmethod
    def _cosine_sim(a: list, b: list) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _text_sim(a: str, b: str) -> float:
        return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def lookup(self, question: str) -> Optional[str]:
        if not self.entries:
            return None

        if self._openai_client:
            question_embedding = self._embed(question)
            best, best_score = None, 0.0
            for entry in self.entries:
                if entry.embedding is None:
                    entry.embedding = self._embed(entry.question)
                score = self._cosine_sim(question_embedding, entry.embedding)
                if score > best_score:
                    best, best_score = entry, score
        else:
            best, best_score = None, 0.0
            for entry in self.entries:
                score = self._text_sim(question, entry.question)
                if score > best_score:
                    best, best_score = entry, score

        if best and best_score >= self.similarity_threshold:
            return best.answer
        return None

    def store(self, question: str, answer: str):
        secret_filter = SecretsFilter()
        if secret_filter.contains_secret(question) or secret_filter.contains_secret(answer):
            return
        embedding = self._embed(question) if self._openai_client else None
        self.entries.append(
            CacheEntry(question=question, answer=answer, embedding=embedding)
        )


class Autopilot:
    def __init__(
        self,
        size_threshold_chars: int = 4000,
        cache_similarity_threshold: float = 0.90,
    ):
        self.trimmer = Trimmer(size_threshold_chars=size_threshold_chars)
        self.cache = SemanticCache(similarity_threshold=cache_similarity_threshold)
        self.secrets_filter = SecretsFilter()

    def handle(self, message: str, call_llm_fn: Callable[[str], str]) -> dict:
        """Route a message through the cache, trimmer, or LLM."""
        if self.secrets_filter.contains_secret(message):
            payload = message
            if self.trimmer.should_trim(payload):
                payload = self.trimmer.trim(payload)
            answer = call_llm_fn(payload)
            return {
                "route": "sensitive_no_cache",
                "answer": answer,
                "cost_estimate": len(payload),
                "sent_chars": len(payload),
                "cached": False,
            }

        cached_answer = self.cache.lookup(message)
        if cached_answer is not None:
            return {
                "route": "cache_hit",
                "answer": cached_answer,
                "cost_estimate": 0,
                "sent_chars": 0,
                "cached": True,
            }

        if self.trimmer.should_trim(message):
            payload = self.trimmer.trim(message)
            route = "trimmed"
        else:
            payload = message
            route = "passthrough"

        answer = call_llm_fn(payload)
        self.cache.store(message, answer)

        return {
            "route": route,
            "answer": answer,
            "cost_estimate": len(payload),
            "sent_chars": len(payload),
            "cached": True,
        }


if __name__ == "__main__":
    def fake_llm(prompt: str) -> str:
        return f"[LLM ANSWER for: {prompt[:40]}...]"

    pilot = Autopilot(size_threshold_chars=50)
    print(pilot.handle("What's the capital of India?", fake_llm))
    print(pilot.handle("India's capital city?", fake_llm))
    print(pilot.handle("x" * 200, fake_llm))
    print(
        pilot.handle(
            "my api_key: sk-abc123XYZsecretvalue000000",
            fake_llm,
        )
    )
    print(len(pilot.cache.entries))
