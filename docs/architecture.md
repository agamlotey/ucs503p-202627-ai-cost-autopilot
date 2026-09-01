# Architecture

AI Cost Autopilot is a single **gateway** that wires three cooperating
components. Coding agents connect to it by pointing their "base URL" at the
gateway; it speaks the OpenAI/Anthropic API format, so no workflow changes.

## Request flow

![Request flow: a coding agent posts to the gateway, which snapshots the
request, computes signals, asks the autopilot for a plan, checks the cache
(returning early on a hit), trims, forwards to the LLM, stores the response
against the original request, and returns
it.](assets/img/request-flow.svg){ width="820" }

The cache always keys on the **original** request (before trimming), so a
trimmed request can still be reused later.

## The three components

- **[Compiler-Aware Trimmer](components/trimmer.md)** — understands code
  structure and sends only what is needed.
- **[Semantic Cache](components/cache.md)** — reuses answers to equivalent
  questions.
- **[Autopilot](components/autopilot.md)** — picks the cheapest safe action per
  request.

Each is developed and tested independently against a frozen interface
(`gateway/interfaces.py`); the gateway is the only place they meet.

## Proof of concept (honest status)

We validated the core idea **before** building our own system. Routing the
open-source TestZeus/Hercules agent through a proxy with off-the-shelf prompt
compression produced:

- ~25% fewer tokens used
- ~17% cheaper per run
- No change in agent behaviour across repeated runs

These numbers come from **existing tools** (Headroom compression + a LiteLLM
proxy), not our system — they prove the approach is real and safe. Our target
for the purpose-built system is **up to ~40%** savings on code-heavy, repetitive
workloads.

## Tech stack

Python, FastAPI (gateway), httpx (forwarding), tree-sitter (parsing), tiktoken
(token counting), sentence-transformers (cache embeddings), SQLite/FAISS (vector
store), pytest + GitHub Actions (CI). The gateway has an offline **mock mode** so
the pipeline runs with no API key and no cost.
