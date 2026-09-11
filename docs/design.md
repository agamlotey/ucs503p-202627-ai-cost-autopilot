# Design

The four design diagrams for AI Cost Autopilot, each covering a different view of
the same system:

| Diagram | Question it answers |
|---|---|
| [Use case diagram](#use-case-diagram) | Who uses the system, and for what? |
| [Data flow diagram](#data-flow-diagram) | Where does data go, and what transforms it? |
| [ER diagram](#entity-relationship-diagram) | What data does the system hold, and how is it related? |
| [Activity diagram](#activity-diagram) | In what order do things happen, and who does each step? |

The semester schedule is on the [Roadmap](roadmap.md#gantt-chart) as a Gantt chart.

## Use case diagram

![Use case diagram: the Developer and the Coding Agent send coding requests.
Sending a request always includes reducing token cost, which includes selecting
the cheapest safe action, which includes reporting savings. Reusing a past
answer, reducing code context and obtaining a completion each conditionally
extend the selection step. The Maintainer configures the gateway and runs the
benchmark.](assets/img/use-case.svg){ width="900" }

- **Actors:** the Developer, the Coding Agent (Cursor, Codex), the Maintainer, and
  the LLM Provider.
- **«include»** means the base use case always performs the included one, so every
  request goes through cost reduction and plan selection.
- **«extend»** means optional behaviour that only runs under a condition. Reusing a
  past answer runs on a cache hit, reducing code context runs when the request is
  over the token budget, and obtaining a completion runs on a cache miss.

## Data flow diagram

![Data flow diagram with three levels. Level 0 shows the gateway between the
coding agent, the LLM provider and the developer. Level 1 breaks the gateway into
six processes and two data stores. Level 2 breaks the Trim Context process into
seven steps.](assets/img/dfd-all-levels.svg){ width="900" }

All three levels are drawn in one diagram, in Gane and Sarson notation:

- **Level 0 (context):** the whole system as one process, with its external
  entities.
- **Level 1:** the gateway as six processes (compute signals, decide plan, look up
  cache, trim context, forward request, record metrics) and two data stores
  (D1 Semantic Cache, D2 Metrics Log).
- **Level 2:** process 4.0, the compiler-aware trimmer, as seven steps from parsing
  the code to measuring the tokens saved.

## Entity relationship diagram

![ER diagram in Chen notation. A Request is logged as one Metric Record, is
forwarded to one LLM Model, may reuse one Cache Entry, and includes many Source
Files. A Source File defines many Functions, and a Function calls other
Functions.](assets/img/er-diagram.svg){ width="900" }

This is the **conceptual** data model, in Chen notation. It covers the gateway's
data stores (cache entries and metric records) and the trimmer's model of the
code it reads (source files, functions and the calls between them).

| Notation | Example in this model |
|---|---|
| Key attribute (underlined) | `request_id`, `hard_key`, `file_path` |
| Multivalued attribute (double oval) | `messages`: a request holds many messages |
| Derived attribute (dashed oval) | `tokens_saved` = `tokens_before` − `tokens_after`; `token_count` |
| Composite attribute | `price` is made of `input_price` and `output_price` |
| 1 : 1 | a Request is logged as exactly one Metric Record |
| 1 : N | a Source File defines many Functions |
| N : 1 | many Requests can reuse the same Cache Entry |
| M : N | a Request includes many Source Files, and a file appears in many Requests |

`calls` is a **recursive** relationship: both ends are Function, one as the
caller and one as the callee. This is the call graph the trimmer builds to decide
which function bodies to keep.

## Activity diagram

![Activity diagram with six swimlanes: Coding Agent, Gateway, Autopilot,
Semantic Cache, Trimmer and LLM Provider. The request is snapshotted, signals are
computed in parallel, the autopilot decides the plan, the cache is checked, the
request is trimmed if needed, forwarded, and the response is stored and metrics
recorded in parallel before it is returned.](assets/img/activity-diagram.svg){ width="900" }

The activity diagram follows one request through the gateway, with one swimlane
per component so it is clear who performs each step. It uses:

- **Decisions** (diamonds with `[yes]` / `[no]` guards): whether to use the cache,
  whether the cache hit, and whether to trim. Each decision has a matching
  **merge** where the branches rejoin.
- **Fork and join bars** for work with no ordering between it: counting tokens and
  detecting code happen in parallel, and so do storing the response and recording
  metrics.
- **An early exit** on a cache hit: the stored response goes straight back to the
  agent and the LLM is never called. This is where the cache saves money.

The cache is always keyed on the **original** request, taken before trimming, so a
trimmed request can still be reused later.

!!! note "Designed, not yet built"
    Recording metrics (DFD process 6.0, data store D2, and the Metric Record
    entity) is part of the design, but the gateway does not store metrics yet.
    Everything else in these diagrams matches the current code in
    `code/gateway/app.py`.
