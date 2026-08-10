"""
Compiler-Aware Trimmer  —  OWNER: Agam

Goal: shrink the request by understanding code STRUCTURE, not by cutting text
blindly. Keep the file the developer is working on (plus what it directly
depends on) in full; collapse every other function/class to its signature.

Pipeline to build:
  1. Parse code into an AST (tree-sitter).
  2. Build a dependency graph (what uses what).
  3. Find the task focus (current file / referenced files).
  4. Keep focus + 1-2 hop dependencies in full.
  5. Collapse everything else to signatures (drop bodies).

Must never break syntax or type signatures (deterministic, compiler-style).
"""
from gateway.interfaces import Message, Stats


class CodeTrimmer:
    def trim(self, messages: list[Message], token_budget: int, ctx: dict) -> tuple[list[Message], Stats]:
        # TODO(Agam): implement the pipeline above.
        # For now this is a safe passthrough so the gateway runs end-to-end.
        stats: Stats = {"tokens_before": 0, "tokens_after": 0, "tokens_saved": 0}
        return messages, stats
