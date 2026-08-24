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

## Status and next steps

- [x] Collapse Python function/method bodies to signatures
- [x] Call graph + focus expansion
- [ ] Cross-file dependency resolution
- [ ] A second language (TypeScript)
