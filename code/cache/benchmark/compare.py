"""Compare cache and trimmer savings on the same scripted notes_api requests.

From code/: python -m cache.benchmark.compare
"""
from unittest.mock import patch

from fastapi.testclient import TestClient

from cache.cache import SemanticCache
from gateway import app as gateway
from gateway.metrics import Metrics
from trimmer.fixtures.loader import as_messages
from trimmer.trimmer import count_tokens


def measure(session, use_cache, use_trimmer):
    decide = gateway.autopilot.decide
    metrics = Metrics()

    def policy(request, signals):
        plan = decide(request, signals)
        return {**plan, "use_cache": use_cache and plan["use_cache"],
                "trim": use_trimmer and plan["trim"]}

    with (
        patch.object(gateway.autopilot, "decide", policy),
        patch.object(gateway, "cache", SemanticCache()),
        patch.object(gateway, "metrics", metrics),
        patch.object(gateway.config, "MOCK_PROVIDER", True),
        patch.object(gateway.config, "TOKEN_BUDGET", 1000),
        patch.object(gateway.provider, "forward", wraps=gateway.provider.forward) as forward,
        TestClient(gateway.app) as client,
    ):
        output_tokens = 0
        for messages in session:
            previous_calls = forward.await_count
            response = client.post("/v1/chat/completions", json={
                "model": "gpt-4o-mini", "messages": messages,
            })
            response.raise_for_status()
            reply = response.json()["choices"][0]["message"]["content"]
            if forward.await_count > previous_calls:
                output_tokens += count_tokens(reply)
        return forward.await_count, metrics.sent_tokens, output_tokens


def main():
    initial = as_messages("fix create_note")
    follow_up = initial + [
        {"role": "assistant", "content": "I will inspect create_note and its validator."},
        {"role": "user", "content": "Which validation error reaches the caller?"},
    ]
    print("Mock provider. Tokens count message text only. Each row starts with an empty cache.")
    for workload, session in [("Exact repeat", [initial, initial]),
                              ("Multi-turn (fixed history)", [initial, follow_up])]:
        print(f"\n{workload}\n{'Mode':16} {'Calls':>6} {'Input':>8} {'Output':>8}")
        for mode, cache, trim in [("Off", False, False), ("Trimmer only", False, True),
                                  ("Cache only", True, False), ("Both", True, True)]:
            calls, sent, output = measure(session, cache, trim)
            print(f"{mode:16} {calls:6} {sent:8} {output:8}")


if __name__ == "__main__":
    main()
