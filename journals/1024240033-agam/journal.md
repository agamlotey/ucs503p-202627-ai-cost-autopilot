# Weekly Progress Journal: Agampreet Kaur (Roll No: 1024240033)

**Project Name:** AI Cost Autopilot (a compiler-aware gateway for token-cost optimisation in LLM coding agents)  
**Component:** Compiler-Aware Trimmer

---

## Week 1: Freezing shared interfaces so three people can build in parallel

### Context
Our project splits into three parts with one owner each: the trimmer (me), the
semantic cache (Devansh), and the autopilot (Furmaan). All three plug into one
FastAPI gateway. The risk in a 3-person build is that everyone waits on everyone
else, and small changes to one module keep breaking the others.

### Problem
If we start writing logic before agreeing on how the modules talk to each other,
every integration becomes a merge conflict, and no one can test their part alone.

### Key Observation
We do not need each other's *code* to start — we only need each other's
*interface* (what goes in, what comes out). If the interfaces are fixed first,
each person can build against a mock of the others.

### Solution
We defined the three contracts as Python `Protocol` types in
`code/gateway/interfaces.py` and agreed not to change them without all three
approving:

```python
class Trimmer(Protocol):
    def trim(self, messages, token_budget, ctx) -> tuple[list, dict]: ...

class Cache(Protocol):
    def lookup(self, request) -> dict | None: ...
    def store(self, request, response) -> None: ...

class Autopilot(Protocol):
    def decide(self, request, signals) -> dict: ...
```

Each folder (`trimmer/`, `cache/`, `autopilot/`) now owns a separate directory,
so we rarely touch the same file. With the contracts frozen, I can develop and
unit-test the trimmer using fake message lists, before the cache or autopilot are
even finished.

### Takeaway
Agree on interfaces before logic. It converted a blocking dependency into three
independent workstreams.

---

## Week 2: Collapsing Python function bodies without breaking indentation

### Context
My part of AI Cost Autopilot is the compiler-aware trimmer. The v1 goal is to
take a Python file and replace every function body with `...`, keeping the
signature and docstring, so the model still sees the *shape* of the code at a
fraction of the tokens. I used `tree-sitter` to parse the source into an AST and
then splice out the bodies.

### Problem
My first attempt rebuilt the collapsed code by inserting `\n    ...` in place of
each body. The indentation kept coming out wrong — doubled for top-level
functions and broken for methods inside a class:

```
def parse_config(path):
        ...        # wrong: extra indent
```

I was *guessing* the indentation instead of reading it from the tree.

### Key Observation
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

### Solution
For each `function_definition`, take its `body` node and replace just that byte
range:

```python
body = fn.child_by_field_name("body")
indent = " " * body.start_point[1]          # the body's own indent
doc = _docstring(body, data)                 # leading string literal, or None
repl = f"{doc}\n{indent}..." if doc else "..."
edits.append((body.start_byte, body.end_byte, repl.encode()))
```

### Gotcha: apply edits back-to-front
Every replacement changes the byte-length of the string, which shifts all offsets
after it. Applying edits front-to-back makes the next `start_byte` point to the
wrong place. Sorting by `start_byte` **descending** and applying last-to-first
keeps earlier offsets valid:

```python
for start, end, repl in sorted(edits, key=lambda e: e[0], reverse=True):
    data = data[:start] + repl + data[end:]
```

### Result
Collapsed output is valid Python (checked with `compile()`), signatures and
docstrings survive, bodies become `...`, and `tiktoken` confirms the token count
drops. Five tests pass.

### Takeaway
When editing source through an AST, read positions from the tree
(`start_point.column`, `start_byte`) instead of guessing, and apply multiple
edits back-to-front so byte offsets stay valid.

---

## Week 3: A false call-graph edge from `super().__init__()`

### Context
The trimmer decides what to keep by building a **call graph** — a map of which
function calls which. Starting from the function the user is working on (the
"focus"), it walks that graph a couple of hops and keeps those functions in
full. Everything else is collapsed to a signature. So the graph is what decides
how much we save: a wrong edge means we keep code the task never needed.

### Problem
While checking the trimmer end to end I printed the graph for our sample
project and saw this:

```python
{'__init__': ['__init__'], 'parse_config': [], 'validate': [], 'run': [...]}
```

`__init__` appeared to call **itself**. Nothing in the file does that.

### Relevant context
The only `__init__` in the fixture is a plain exception class:

```python
class ConfigError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)
```

### Key Observation
The bug was in how I resolved the *name* of a called function. In tree-sitter, a
call like `obj.method()` is an `attribute` node, and I was resolving it by
taking the bare attribute name:

```python
if fn_node.type == "attribute":       # obj.method(...) -> "method"
    attr = fn_node.child_by_field_name("attribute")
    return text_of(attr)
```

So `super().__init__(message)` resolved to the name `"__init__"`, which matched
the `__init__` **defined in this file** — and the graph recorded an edge from
`__init__` to itself. The call is real, but its target is the *base class*, not
anything in our file.

### Solution
Two changes. First, ignore calls whose receiver is `super()`, by checking the
attribute node's `object` field:

```python
if fn_node.type == "attribute":
    obj = fn_node.child_by_field_name("object")
    if obj is not None and obj.type == "call":
        inner = obj.child_by_field_name("function")
        if inner is not None and text_of(inner) == "super":
            return ""          # dispatches to the base class, not to us
    ...
```

Second, drop self-edges when building the graph, since a function is already in
the set when we expand from it, so recursion tells us nothing:

```python
edges = {c for c in calls_in(body) if c != caller}
```

Result:

```python
{'__init__': [], 'parse_config': [], 'validate': [], 'run': ['parse_config', 'validate']}
```

### Caveat I left in the code
Attribute calls are still matched by bare method name, so `x.parse_config()`
will link to a module-level `parse_config` even if `x` is unrelated. I left that
in deliberately and documented it: an extra edge makes the trimmer keep **more**
than needed (we lose savings), while a missing edge would drop context the model
actually needed. When the two failure modes are not equal, bias the
approximation towards the harmless one.

### Takeaway
When matching identifiers from an AST, the node's *name* is not its *target*.
`super().__init__()` and `self.__init__()` produce the same attribute text and
mean completely different things — the receiver has to be part of the decision.
