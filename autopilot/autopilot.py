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

import os
import re
import time
import difflib
import hashlib
from dataclasses import dataclass, field
from typing import Callable, Optional


# ----------------------------------------------------------------------
# 1. TRIMMER  (compresses large / repetitive / boilerplate-heavy input)
# ----------------------------------------------------------------------
class Trimmer:
    """
    Cuts the fat out of a message while protecting the parts that matter
    (explicit instructions, questions, code blocks).

    Strategy (mirrors what your Headroom report found it actually does):
      - Collapse excess whitespace/newlines.
      - Strip HTML/markup noise if a raw webpage dump was pasted in.
      - Deduplicate repeated lines/paragraphs (common in scraped content).
      - Never touch text inside instruction markers or code fences.
    """

    # Anything wrapped in these is treated as "protected" and left untouched.
    PROTECTED_PATTERNS = [
        r"```.*?```",              # code blocks
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

        # Strip obvious HTML tags (webpage dumps)
        stashed_text = re.sub(r"<[^>]+>", " ", stashed_text)

        # Collapse whitespace
        stashed_text = re.sub(r"[ \t]+", " ", stashed_text)
        stashed_text = re.sub(r"\n{3,}", "\n\n", stashed_text)

        # Deduplicate repeated lines (keep first occurrence, preserve order)
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

        # Restore protected sections
        for i, block in enumerate(protected):
            result = result.replace(f"__PROTECTED_{i}__", block)

        return result


# ----------------------------------------------------------------------
# 2. SEMANTIC CACHE  (remembers past answers, matches "means the same")
# ----------------------------------------------------------------------
@dataclass
class CacheEntry:
    question: str
    answer: str
    embedding: Optional[list] = None
    created_at: float = field(default_factory=time.time)


class SemanticCache:
    """
    In-memory semantic cache. Swap the storage layer for Redis/Postgres+pgvector
    later — the interface (lookup / store) stays the same.
    """

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

    # ---- embeddings (optional, better matching) ----
    def _embed(self, text: str) -> Optional[list]:
        if not self._openai_client:
            return None
        resp = self._openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return resp.data[0].embedding

    @staticmethod
    def _cosine_sim(a: list, b: list) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # ---- fallback similarity (no API key needed, zero cost) ----
    @staticmethod
    def _text_sim(a: str, b: str) -> float:
        return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def lookup(self, question: str) -> Optional[str]:
        if not self.entries:
            return None

        if self._openai_client:
            q_emb = self._embed(question)
            best, best_score = None, 0.0
            for entry in self.entries:
                if entry.embedding is None:
                    entry.embedding = self._embed(entry.question)
                score = self._cosine_sim(q_emb, entry.embedding)
                if score > best_score:
                    best, best_score = entry, score
            if best and best_score >= self.similarity_threshold:
                return best.answer
            return None
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
        embedding = self._embed(question) if self._openai_client else None
        self.entries.append(CacheEntry(question=question, answer=answer, embedding=embedding))


# ----------------------------------------------------------------------
# 3. AUTOPILOT  (the decision logic: cache -> trim -> passthrough)
# ----------------------------------------------------------------------
class Autopilot:
    def __init__(
        self,
        size_threshold_chars: int = 4000,
        cache_similarity_threshold: float = 0.90,
    ):
        self.trimmer = Trimmer(size_threshold_chars=size_threshold_chars)
        self.cache = SemanticCache(similarity_threshold=cache_similarity_threshold)

    def handle(self, message: str, call_llm_fn: Callable[[str], str]) -> dict:
        """
        call_llm_fn: a function you provide that takes a (possibly trimmed)
        string and returns the LLM's answer, e.g.:

            def call_llm_fn(prompt: str) -> str:
                resp = openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                )
                return resp.choices[0].message.content
        """
        # Step 1: seen this before (or something that means the same)?
        cached_answer = self.cache.lookup(message)
        if cached_answer is not None:
            return {
                "route": "cache_hit",
                "answer": cached_answer,
                "cost_estimate": 0,
                "sent_chars": 0,
            }

        # Step 2: is it big/boilerplate-heavy? trim it first.
        if self.trimmer.should_trim(message):
            payload = self.trimmer.trim(message)
            route = "trimmed"
        else:
            payload = message
            route = "passthrough"

        answer = call_llm_fn(payload)

        # Save to cache for next time (store under the ORIGINAL question,
        # so future semantically-similar questions still match).
        self.cache.store(message, answer)

        return {
            "route": route,
            "answer": answer,
            "cost_estimate": len(payload),  # swap for real token-based costing
            "sent_chars": len(payload),
        }


# ----------------------------------------------------------------------
# Quick manual test
# ----------------------------------------------------------------------
if __name__ == "__main__":
    def fake_llm(prompt: str) -> str:
        return f"[LLM ANSWER for: {prompt[:40]}...]"

    pilot = Autopilot(size_threshold_chars=50)

    print(pilot.handle("What's the capital of India?", fake_llm))
    print(pilot.handle("India's capital city?", fake_llm))  # should hit cache
    print(pilot.handle("x" * 200, fake_llm))                # should trim
