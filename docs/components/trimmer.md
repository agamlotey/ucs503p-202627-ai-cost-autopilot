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
5. **Keep the constructors** of any class reached, because instantiating a
   class runs its `__init__`. Constructors are tracked by qualified name
   (`ConfigError.__init__`), so keeping one class's constructor does not keep
   every `__init__` in the request.
6. **Collapse** every other function/method body to `...`, keeping its
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
saves more only because it throws away the function being fixed. Across five
tasks on this fixture the trimmer saves **33.1% to 48.3%**; the most connected
functions (`create_note`, `update_note`) are the hardest cases, because more of
the project genuinely is a dependency.

Reproduce it from `code/`:

``` shell
python -m trimmer.benchmark.baselines
python -m trimmer.benchmark.baselines --task "fix delete_note"
```

### Does the saving generalise?

One fixture cannot answer that, because the trimmer keys on code shape. A
second project, `ledger_cli`, is deliberately unlike the first: a command line
tool with a four-deep exception hierarchy and a stateful class, so five classes
define a constructor where `notes_api` has one.

| Project | Task | Tokens | Saved | Kept in full | Context |
|---|---|---:|---:|---:|---|
| `notes_api` | fix create_note | 2,166 of 3,277 | 33.9% | 18 of 45 | complete |
| `notes_api` | fix delete_note | 1,694 of 3,277 | 48.3% | 7 of 45 | complete |
| `ledger_cli` | fix parse_row | 1,586 of 2,472 | 35.8% | 10 of 37 | complete |
| `ledger_cli` | fix validate | 1,240 of 2,472 | 49.8% | 6 of 37 | complete |
| `ledger_cli` | fix render | 1,252 of 2,472 | 49.4% | 5 of 36 | complete |

Mean saving: **41.1%** on `notes_api`, **45.0%** on `ledger_cli`. Every output
still compiles.

"Context" is the part token counts cannot show. For each task the functions a
correct patch has to read are written down by hand, from the fix rather than
from the trimmer's output, and checked to still be present in full. A reduction
that drops something the fix needs is not a saving, it is a wrong answer that
happens to be cheaper. CI runs this check.

`ledger_cli` also ships its own passing test suite (13 tests), which is not sent
as context. That is what makes the next step possible: judging a patch written
against trimmed context by the project's own tests instead of by eye.

``` shell
python -m trimmer.benchmark.projects
python -m trimmer.benchmark.projects --markdown
```

### Does a real model still fix the bug?

Token counts and context checks are both static. The last question is whether
a real model, given only what the trimmer kept, still produces a patch that
passes the project's own tests.

`agent_run.py` injects one real bug into `ledger_cli`, confirms the suite now
fails, then asks the model to fix it twice: once with the whole project, once
with the trimmed context. Each answer is applied to a fresh copy and judged by
the project's own 13 tests. The bug is deliberately **not** in the function the
task names: the task points at `parse_row`, the fault is in
`LedgerError._describe`, two steps away through a constructor and a `super()`
call. That is the case the trimmer used to get wrong.

Across 22 trials with `gpt-4o-mini`:

| Condition | Tokens sent | Fixed it |
|---|---:|---:|
| Full context | 2,769 | 13 of 22 |
| Trimmed context | 2,303 (16.8% fewer) | 13 of 22 |

The same success rate on 16.8% fewer tokens. The model succeeds on roughly
three runs in five either way, so this task sits at the edge of what
`gpt-4o-mini` can do, and a single run proves nothing: use `--trials`.

**It also found a real design gap.** A model answering with whole files hands
the elision back as if it were code, and applying that answer deletes working
functions. In the first runs this wiped three bodies in `dates.py` and dropped
the suite to 5 of 13, which looks exactly like "the trimmer cut too much" and
is not. The gateway is what replaced those bodies, so the gateway is what can
restore them: the benchmark re-expands every elided body before applying an
answer, and reports what it restored. Trimming is only safe for a write-back
workflow if something puts back what it took out. Doing that inside the
gateway rather than in the benchmark is the next piece of work.

``` shell
python -m trimmer.benchmark.agent_run --trials 6
```

## Status and next steps

- [x] Collapse Python function/method bodies to signatures
- [x] Call graph + focus expansion
- [x] Cross-file dependency resolution
- [x] Benchmark against simple baselines (`trimmer/benchmark/`)
- [x] Class instantiation edges (`raise ConfigError(...)` keeps that class's constructor)
- [x] A second project, with a context-sufficiency check in CI
- [x] Run a real model against trimmed context and judge the patch by
      `ledger_cli`'s own tests (`trimmer/benchmark/agent_run.py`)
- [ ] Re-expansion in the gateway itself, so a trimmed reply can be written
      back safely without the benchmark doing it
- [ ] A second language (TypeScript)
