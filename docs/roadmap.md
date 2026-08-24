# Roadmap

## Milestones

| Milestone | Goal |
|---|---|
| **M1** | Gateway pass-through working; shared interfaces frozen |
| **M2** | Each component working on its own (with mocks) |
| **M3** | All three integrated; token savings measured |
| **M4** | Polish, benchmark, and final demo |

## Semester plan

| Week | Task | Deliverable |
|---|---|---|
| W4 | Project proposal | Proposal report |
| W5–W6 | Gateway pass-through; freeze interfaces; v1 of each module | Running gateway |
| W7 | Prototype: Python trimmer, exact-match cache, basic autopilot, end-to-end | **Prototype demo (MST)** |
| W8 | Improvement plan from prototype feedback | Improvement plan |
| W9–W10 | MST period | — |
| W11–W12 | Semantic cache, second language, autopilot tuning; integrate and measure | Integrated build + metrics |
| W13 | Buffer (holiday week) | — |
| W14–W15 | Full integration; benchmark across tools | **Second prototype** |
| W16 | Improvements over second prototype | Refined build |
| W17 | Final prototype, presentation, report | **Final deliverable (EST)** |

## Success criteria

- **≥ 30%** token reduction on code-heavy, repetitive workloads
- **Zero** behavioural regressions — the agent reaches the same outcome with and
  without the gateway
- Works with at least two different coding agents through a single endpoint

## Risks and mitigation

| Risk | Mitigation |
|---|---|
| Language-specific parsing is complex | Start with Python; fall back to safe pass-through when a file cannot be parsed |
| Cache returns a wrong "close" answer | Conservative similarity threshold; behavioural checks; never cache secrets |
| Provider APIs change | Isolate provider specifics behind a thin adapter |
| Scope creep | Milestone-driven: one language and one provider first |
