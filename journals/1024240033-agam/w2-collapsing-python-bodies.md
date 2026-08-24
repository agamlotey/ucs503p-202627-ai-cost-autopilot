# Week 2 : Collapsing Python function bodies without breaking indentation

## Context
My part of AI Cost Autopilot is the compiler-aware trimmer. The v1 goal is to
take a Python file and replace every function body with `...`, keeping the
signature and docstring, so the model still sees the *shape* of the code at a
fraction of the tokens. I used `tree-sitter` to parse the source into an AST and
then splice out the bodies.

## Problem
My first attempt rebuilt the collapsed code by inserting `\n    ...` in place of
each body. The indentation kept coming out wrong — doubled for top-level
functions and broken for methods inside a class:

```
def parse_config(path):
        ...        # wrong: extra indent
```

I was *guessing* the indentation instead of reading it from the tree.

## Key Observation
I printed the byte range of the `block` node (the function body) and found that
**the indentation before the first statement is not part of the block node** —
the block starts at the first non-space character, and the leading spaces are
already in the source:

```
def parse_config(path):\n    """doc"""...
                        ^ block.start_byte  (the 4 spaces before are already there)
```

Also, `block.start_point.column` equals the body's indent width (4 for a
top-level function, 8 for a method). So I do **not** need to add indentation
before `...` — I only need it when I insert a *second* line to keep the
docstring.

## Solution
For each `function_definition`, take its `body` node and replace just that byte
range:

```python
body = fn.child_by_field_name("body")
indent = " " * body.start_point[1]          # the body's own indent
doc = _docstring(body, data)                 # leading string literal, or None
repl = f"{doc}\n{indent}..." if doc else "..."
edits.append((body.start_byte, body.end_byte, repl.encode()))
```

## Gotcha: apply edits back-to-front
Every replacement changes the byte-length of the string, which shifts all offsets
after it. Applying edits front-to-back makes the next `start_byte` point to the
wrong place. Sorting by `start_byte` **descending** and applying last-to-first
keeps earlier offsets valid:

```python
for start, end, repl in sorted(edits, key=lambda e: e[0], reverse=True):
    data = data[:start] + repl + data[end:]
```

## Result
Collapsed output is valid Python (checked with `compile()`), signatures and
docstrings survive, bodies become `...`, and `tiktoken` confirms the token count
drops. Five tests pass.

## Takeaway
When editing source through an AST, read positions from the tree
(`start_point.column`, `start_byte`) instead of guessing, and apply multiple
edits back-to-front so byte offsets stay valid.
