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

---

## Week 4: A toy fixture hid a cross-file dependency bug

### Context
Until now every trimmer test ran on `sample_project`: two files, four functions,
43 lines. The trimmer's whole job is *selective* retention, keeping the functions
a task needs and collapsing the rest. To measure that honestly I built a realistic
fixture, `notes_api`: a small notes service with 10 files, 45 functions and
3,277 tokens, split into handlers, validators, serializers, auth, db and utils,
with real imports between them.

### Problem
The first run on the new fixture, with the task "fix create_note", kept
`create_note` in full but collapsed `validate_note` to its signature. That is
the one function the fix is most likely to need:

```python
# handlers/notes.py
def create_note(headers, payload):
    """Validate and store a new note for the current user."""
    user_id = current_user(headers)
    clean = validate_note(payload)      # defined in validators.py
    ...
```

### Key Observation
A coding agent sends one file per message, and I built one call graph **per
message**. When resolving calls, "known" meant "defined in this same file", so
`validate_note(...)` inside `handlers/notes.py` matched nothing and the edge was
never recorded. The toy project could not catch this: with 4 functions in 2 files
nearly everything was reachable anyway, so a missing edge changed nothing. The
test input was too small to fail.

### Solution
Build **one** graph across every code message, resolving each call against the
union of all names defined anywhere in the request:

```python
def merge_call_graphs(sources):
    defined_all = set()
    for src in sources:
        defined_all |= _defined_functions(src)
    graph = {}
    for src in sources:
        for caller, callees in build_call_graph(src, known=defined_all).items():
            graph.setdefault(caller, set()).update(callees)
    return graph, defined_all
```

`CodeTrimmer.trim()` now expands the focus once over this merged graph, then
collapses each message with the functions that message defines. A regression
test puts the focus function and its dependency in separate messages and checks
that the dependency keeps its body.

### Takeaway
The size and shape of a fixture are part of the test. A bug that only appears
when code is spread across files will never appear in a two-file project, so
realistic inputs are not optional for a component whose purpose is to be
selective.

---

## Week 5: Getting «include» and «extend» the right way round

### Context
This week I drew the design diagrams: a data flow diagram with levels 0, 1 and 2
in one figure, and a UML use case diagram. The use case diagram has one base
flow (a coding agent sends a request) and several behaviours that only happen
sometimes.

### Problem
My first version was wrong in two ways. I used «extend» for steps that happen on
every request, and I pointed the «extend» arrows from the base use case to the
optional one, the same direction as «include». It also looked messy: some arrow
heads finished inside the ellipses, and labels sat on top of other arrows.

### Key Observation
The two relationships differ in *who depends on whom*:

- **«include»**: the base use case **always** performs the included one and
  cannot finish without it. The arrow goes **base → included**. "Send coding
  request" always includes "Reduce token cost", which always includes "Select
  cheapest safe action".
- **«extend»**: optional behaviour that runs only under a condition. The base is
  complete without it and does not even know it exists, so the arrow goes
  **extension → base**. "Reuse past answer" (on a cache hit), "Reduce code
  context" (over the token budget) and "Obtain completion" (on a miss) each
  extend "Select cheapest safe action".

The quick test: *can the base use case finish without this?* If not, it is an
include. If yes, and it only sometimes happens, it is an extend.

### Solution
I redrew the include chain as a vertical column and moved the three extensions
to the right, each pointing back at the base. To stop arrow heads ending inside a
bubble, I computed each end point on the ellipse boundary instead of guessing.
For the base ellipse (centre 500, 470; radii 115 and 36), the point
(545, 437) satisfies

```
((545 - 500) / 115)^2 + ((437 - 470) / 36)^2 = 0.153 + 0.840 ≈ 1
```

so the arrow stops exactly on the edge. I also checked the label positions
against the arrow lines numerically, after finding that an «include» label sat
exactly where an «extend» diagonal crossed it.

### Takeaway
In UML the direction of an arrow carries meaning, not decoration. «include» and
«extend» look alike, but they say opposite things about which use case depends on
which, and the "can it finish without it?" test settles it every time.

---

## Week 6: A correctness fix that cut our headline number

### Context
For the prototype report I re-measured the trimmer on `notes_api` against simple
baselines, for the task "fix create_note". Earlier I had quoted a saving of about
52% from a measurement taken on the same fixture.

### Problem
The fresh measurement gave **33.9%**, not ~52%. My first guess was a measurement
mistake, so I ran the trimmer from just before the Week 4 cross-file fix on the
same input:

| Trimmer version | Saved | `validate_note` body kept? |
|---|---|---|
| Before the cross-file fix | 53.8% | no |
| Current | 33.9% | yes |

### Key Observation
The old number was not a better trimmer; it was the bug. Part of the "saving"
was `validate_note`, the code the fix needed. A reduction that removes something
the task depends on is not a saving, it is a wrong answer that happens to be
cheaper. Collapsing every function body shows the same trap in its extreme form:
57.0% "saved", but the function being fixed is gone.

Measuring the baselines had two traps of its own. My first script for "strip
comments and docstrings" reported **broken** Python, because deleting a docstring
that is a function's only statement leaves an empty body. The baseline has to
insert `pass` there, or the comparison is against something no one would use.
The second trap was unfair input: the request builder puts a `# file: <path>` line
on top of each file, and I had counted those 56 tokens for the trimmer but not for
the baselines. Measured on the same file contents for every variant, the trimmer's
saving went from 31.9% to 33.9%.

### Solution
I report every variant with a validity check next to it:

| Variant | Saved | Output |
|---|---|---|
| Strip indentation and blank lines | 9.0% | broken |
| Strip comments and docstrings | 20.5% | valid |
| Collapse every function body | 57.0% | valid, but drops the focus |
| **Trimmer (focus + callees, 2 hops)** | **33.9%** | **valid** |

The trimmer keeps 18 of the 45 functions in full (including `validate_note` from
another file) and collapses the other 27. The table now comes from
`python -m trimmer.benchmark.baselines`, and a CI test checks the relationships
it shows, so the numbers can be reproduced with one command.

### Takeaway
Re-measure after every correctness fix, and never report a saving without the
check that the result is still correct. The honest number is smaller, but it is
the one that holds up when someone asks how it was measured.
