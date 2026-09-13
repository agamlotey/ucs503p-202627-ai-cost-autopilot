"""Send prompts to the RUNNING gateway (http://localhost:8000) so the live
dashboard updates. Type a question, get the answer; ask the same thing twice to
see a cache hit on the dashboard.

Start the gateway first (in another terminal), then:  python ask.py
"""
import sys
import httpx

URL = "http://localhost:8000/v1/chat/completions"


def main():
    print("\n  Talking to the live gateway at localhost:8000")
    print("  Ask something. Ask it AGAIN to see a cache hit on the dashboard.")
    print("  Type 'quit' to exit.\n")
    while True:
        try:
            msg = input("  you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not msg:
            continue                       # ignore blank lines (don't quit)
        if msg.lower() in ("quit", "exit"):
            break
        body = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": msg}]}
        try:
            r = httpx.post(URL, json=body, timeout=120)
            r.raise_for_status()
            print("  bot >", r.json()["choices"][0]["message"]["content"], "\n")
        except httpx.ConnectError:
            sys.exit("  Can't reach the gateway — is it running on port 8000?")
        except Exception as e:
            print("  error:", e, "\n")


if __name__ == "__main__":
    main()
