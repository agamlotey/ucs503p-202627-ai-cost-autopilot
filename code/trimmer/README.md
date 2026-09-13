# Trimmer (Agam)

Compiler-aware code trimmer. See docstring in `trimmer.py` for the pipeline.

## Done
- [x] Parse Python into an AST using tree-sitter.
- [x] Extract functions/classes + their signatures.
- [x] Collapse non-focus functions to `def name(args) -> ret: ...`.
- [x] Return real token-saving stats (uses `tiktoken`).
- [x] Call graph + focus expansion, resolved across files.

## Benchmark
Compare the trimmer with simple baselines on the realistic fixture:

```bash
python -m trimmer.benchmark.baselines                       # run from code/
python -m trimmer.benchmark.baselines --task "fix delete_note"
python -m trimmer.benchmark.baselines --markdown            # table for the docs
```

Results and what they mean: `docs/components/trimmer.md`.

## Contract (do not change alone)
`trim(messages, token_budget, ctx) -> (trimmed_messages, stats)`
