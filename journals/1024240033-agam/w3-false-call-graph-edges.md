# Week 3 : A false call-graph edge from `super().__init__()`

## Context
The trimmer decides what to keep by building a **call graph** — a map of which
function calls which. Starting from the function the user is working on (the
"focus"), it walks that graph a couple of hops and keeps those functions in
full. Everything else is collapsed to a signature. So the graph is what decides
how much we save: a wrong edge means we keep code the task never needed.

## Problem
While checking the trimmer end to end I printed the graph for our sample
project and saw this:

```python
{'__init__': ['__init__'], 'parse_config': [], 'validate': [], 'run': [...]}
```

`__init__` appeared to call **itself**. Nothing in the file does that.

## Relevant context
The only `__init__` in the fixture is a plain exception class:

```python
class ConfigError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)
```

## Key Observation
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

## Solution
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

## Caveat I left in the code
Attribute calls are still matched by bare method name, so `x.parse_config()`
will link to a module-level `parse_config` even if `x` is unrelated. I left that
in deliberately and documented it: an extra edge makes the trimmer keep **more**
than needed (we lose savings), while a missing edge would drop context the model
actually needed. When the two failure modes are not equal, bias the
approximation towards the harmless one.

## Takeaway
When matching identifiers from an AST, the node's *name* is not its *target*.
`super().__init__()` and `self.__init__()` produce the same attribute text and
mean completely different things — the receiver has to be part of the decision.
