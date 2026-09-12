"""End-to-end prototype demo.

Replays a short coding session through the REAL gateway (mock provider, so it
needs no API key and costs nothing) and shows what the system saves: which
requests hit the cache, which get trimmed, and the total token reduction.

Run from the code/ folder:  python demo.py
"""
from gateway import config
config.MOCK_PROVIDER = True
config.PROVIDER_API_KEY = "sk-demo"

from fastapi.testclient import TestClient
from gateway import app as gw
from gateway import provider
from trimmer.trimmer import count_tokens

BIG_FILE = "def " + "\n".join(
    f"def helper_{i}(x):\n    \"\"\"helper {i}\"\"\"\n    return x + {i}" for i in range(520)
)  # a large file so the trimmer has something to cut

SESSION = [
    ("Explain what run() does", "def run(p):\n    return load(p)"),
    ("Explain what run() does", "def run(p):\n    return load(p)"),          # repeat -> cache
    ("Refactor this module", BIG_FILE),                                       # big -> trim
    ("What is a good commit message style?", None),                           # prose
    ("Explain what run() does", "def run(p):\n    return load(p)"),          # repeat -> cache
    ("Refactor this module", BIG_FILE),                                       # repeat -> cache
]


def main():
    gw.cache.__init__()
    client = TestClient(gw.app)

    # spy on the provider to see the tokens that actually reach it
    sent = {"tokens": 0}
    orig = provider.forward
    async def spy(body):
        txt = "\n".join(m["content"] for m in body.get("messages", [])
                        if isinstance(m.get("content"), str))
        sent["tokens"] = count_tokens(txt)
        return await orig(body)
    gw.provider.forward = spy

    print(f"\n  AI Cost Autopilot — prototype demo  (mock provider, no API key)\n")
    print(f"  {'#':>2}  {'request':<34}{'original':>9}{'sent':>7}  {'what happened'}")
    baseline = total_sent = 0
    for i, (ask, code) in enumerate(SESSION, 1):
        content = ask if code is None else f"{ask}:\n{code}"
        body = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": content}]}
        orig_tokens = count_tokens(content)

        sent["tokens"] = -1
        resp = client.post("/v1/chat/completions", json=body).json()
        if sent["tokens"] == -1:                       # provider never called
            got, what = 0, "CACHE HIT (free)"
        elif sent["tokens"] < orig_tokens:
            got, what = sent["tokens"], f"trimmed {orig_tokens}->{sent['tokens']}"
        else:
            got, what = sent["tokens"], "forwarded"
        baseline += orig_tokens
        total_sent += got
        label = ask[:32]
        print(f"  {i:>2}  {label:<34}{orig_tokens:>9}{got:>7}  {what}")

    saved = baseline - total_sent
    print("\n  " + "-" * 58)
    print(f"  tokens the app would have sent : {baseline}")
    print(f"  tokens the gateway actually sent: {total_sent}")
    print(f"  SAVED                          : {saved}  ({100*saved/baseline:.0f}% less)\n")
    print("  Every request still got an answer — the savings come from reusing")
    print("  repeats and trimming bulky code, with no change to the coding tool.\n")


if __name__ == "__main__":
    main()
