# AI Cost Autopilot

An agentic gateway that cuts AI/LLM costs for coding agents (Cursor, Claude Code, Codex).
It sits between the coding tool and the AI, and on every request it **trims** the code,
**reuses** past answers, and **picks the cheapest safe path** — automatically.

> Status: early build. Idea validated in a proof-of-concept; we are now building our own system.

## The three components (one owner each)
| Component | Folder | Owner | Job |
|-----------|--------|-------|-----|
| Compiler-Aware Trimmer | `trimmer/` | **Agam** | Understands code structure and sends only what's needed |
| Semantic Cache | `cache/` | **Devansh** | Reuses past answers for questions that mean the same thing |
| Autopilot | `autopilot/` | **Furmaan** | Picks the cheapest safe path per request |
| Gateway (shared) | `gateway/` | Lead | FastAPI proxy that wires the three together |

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add your API key
uvicorn gateway.app:app --reload --port 8000
```
Point any OpenAI-compatible tool at `http://localhost:8000/v1`.

## How the pieces connect
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). **Do not change `gateway/interfaces.py`
without all three agreeing** — it's the contract everyone builds against.

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for the branch + PR workflow.
