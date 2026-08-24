# The Problem

AI coding assistants are powerful — and expensive at scale.

## Why the bills explode

- Tools like Cursor, Claude Code, and Copilot send **large chunks of your
  codebase to the model on every request**.
- You pay for every **token** (a small fragment of text), so cost grows with the
  size and number of requests.
- Prompts are often **repetitive** — the same question, or near-identical
  context, is sent again and again.
- Bills are **unpredictable**, so a team cannot plan a budget.

## The hidden risk

Sending your codebase in bulk also means **private code leaves your machine** and
reaches a third-party provider on every call.

## Why existing fixes fall short

Generic "prompt compressors" treat code as plain text and cut it by length or
pattern. That is **unsafe** — they can delete a line of logic the model needed,
breaking correctness.

## Where the money goes

Most AI spend is **avoidable**. A typical request is dominated by:

- Repeated questions
- Bloated prompts
- Code the model never needed to see

…with only a small slice being the code that actually matters. The goal of this
project is to remove that waste **safely**, and reduce how much code leaves the
machine at the same time — see the [Architecture](architecture.md).
