# Trimmer (Agam)

Compiler-aware code trimmer. See docstring in `trimmer.py` for the pipeline.

## First tasks
- [ ] Parse one language (start with Python) into an AST using tree-sitter.
- [ ] Extract functions/classes + their signatures.
- [ ] Collapse non-focus functions to `def name(args) -> ret: ...`.
- [ ] Return real token-saving stats (use `tiktoken`).

## Contract (do not change alone)
`trim(messages, token_budget, ctx) -> (trimmed_messages, stats)`
