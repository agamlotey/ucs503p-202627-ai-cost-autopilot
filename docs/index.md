# AI Cost Autopilot

**UCS503: Software Engineering — Project (2026–27 Odd)**
Thapar Institute of Engineering and Technology, Patiala

A proxy that sits between AI coding agents (Cursor, Claude Code, Codex) and the
LLM they call, and cuts **token cost** and **code exposure** on every request —
automatically, with no change to how developers work.

> **Status:** early build. The core idea is validated by a proof-of-concept
> (see [Architecture](architecture.md)); we are now building our own,
> purpose-built system.

## In one line

*Same brain, smaller bills* — the autopilot for your AI spend.

## Explore

- [The Problem](problem.md) — why AI coding gets expensive
- [Architecture](architecture.md) — the gateway and how it works
- Components:
    - [Compiler-Aware Trimmer](components/trimmer.md) *(Agam)*
    - [Semantic Cache](components/cache.md) *(Devansh)*
    - [Autopilot](components/autopilot.md) *(Furmaan)*
- [Usage](usage.md) — run it locally
- [Roadmap](roadmap.md) — milestones
- [Team](team.md) — who's who

## Repository

The application code lives in the `code/` folder of the
[project repository](https://github.com/agamlotey/ucs503p-202627-ai-cost-autopilot).
