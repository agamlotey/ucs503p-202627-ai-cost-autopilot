# Compiler-Aware Trimmer

**Owner:** Agam (1024240033) · **Code:** `code/trimmer/`

Shrinks a request by understanding code **structure**, not by cutting text
blindly.

## The idea

A generic compressor treats code as plain text and cuts by length or pattern —
which can silently delete a line the model needed. The compiler-aware trimmer
parses the code instead, keeps what the task actually needs in full, and reduces
everything else to its **signature**.

The model still sees the *shape* of the codebase — an interface map, the way a
senior engineer skims a project — at a fraction of the tokens.

## Before and after

Original:

``` python
def parse_config(path):
    """Load and parse a JSON config file."""
    with open(path) as f:
        raw = f.read()
    return json.loads(raw)
```

Collapsed:

``` python
def parse_config(path):
    """Load and parse a JSON config file."""
    ...
```

Signature and docstring survive; the body is gone. The output is still **valid
Python**.

## How it works

1. **Parse** the source with `tree-sitter` into an Abstract Syntax Tree.
2. **Build a call graph** — which function calls which.
3. **Find the focus** — the functions the task is about, taken from
   `ctx["focus"]` or from function names mentioned in the user's plain-text
   messages.
4. **Expand** from the focus across the call graph (breadth-first, a
   configurable number of hops) — the focus *and what it calls* stay in full.
5. **Collapse** every other function/method body to `...`, keeping its
   signature and docstring.

Because it cuts along real code boundaries, it is **deterministic**: it never
breaks syntax or type signatures.

## Budget awareness

`CodeTrimmer.trim()` only trims when the request exceeds the token budget, and
reports what it saved:

``` python
messages, stats = CodeTrimmer().trim(messages, token_budget, ctx)
# stats -> {"tokens_before": …, "tokens_after": …, "tokens_saved": …, "trimmed": bool}
```

Token counts are measured with `tiktoken`. If `tree-sitter` is unavailable, the
trimmer degrades gracefully to a safe pass-through.

## Measured results

On the `notes_api` fixture (10 files, 45 functions, 3,277 tokens), for the task
"fix create_note". Every variant is measured on the same file contents and
checked to still compile.

| Variant | Tokens | Saved | Output |
|---|---:|---:|---|
| raw (no gateway) | 3,277 | 0.0% | valid |
| strip indentation + blank lines | 2,982 | 9.0% | **broken** |
| strip comments + docstrings | 2,606 | 20.5% | valid |
| collapse every function body | 1,410 | 57.0% | valid, drops the focus |
| **trimmer (focus + callees, 2 hops)** | **2,166** | **33.9%** | **valid**, 18 of 45 functions kept in full |

The trimmer beats the simplest safe trick while keeping everything the task
depends on, including `validate_note` from another file. Collapsing every body
saves more only because it throws away the function being fixed. On other tasks
against the same fixture the trimmer saves 47% to 55%; "fix create_note" is the
hardest case because it is the most connected function.

Reproduce it from `code/`:

``` shell
python -m trimmer.benchmark.baselines
python -m trimmer.benchmark.baselines --task "fix delete_note"
```

## Status and next steps

- [x] Collapse Python function/method bodies to signatures
- [x] Call graph + focus expansion
- [x] Cross-file dependency resolution
- [x] Benchmark against simple baselines (`trimmer/benchmark/`)
- [ ] Class instantiation edges (`raise ConfigError(...)` does not yet link to its constructor)
- [ ] A second language (TypeScript)
