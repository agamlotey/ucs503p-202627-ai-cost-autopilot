"""
Compiler-Aware Trimmer  —  OWNER: Agam

v1 (prototype): parse Python with tree-sitter and collapse function/method
bodies to their signatures (keeping the docstring), so the model still sees the
*shape* of the code without paying for every line. Token savings measured with
tiktoken.

Now also: a call graph merged across files, so the focus keeps the functions
it depends on wherever they live, including the constructor of any class it
instantiates and the base constructor that one defers to.

Later: more languages. See trimmer/README.md.

The module degrades gracefully: if tree-sitter isn't installed, `collapse_python`
returns the source unchanged, so the gateway still runs as a passthrough.
"""
from __future__ import annotations

import re

_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# ---- token counting (tiktoken, with a safe offline fallback) ----
try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")
    _enc.encode("warm up")  # force any lazy download now

    def count_tokens(text: str) -> int:
        return len(_enc.encode(text))
except Exception:  # pragma: no cover - offline / tiktoken missing
    def count_tokens(text: str) -> int:
        return max(1, len(text) // 4)


# ---- tree-sitter parser (lazy, optional) ----
_parser = None


def _get_parser():
    global _parser
    if _parser is None:
        import tree_sitter_python as tspython
        from tree_sitter import Language, Parser
        _parser = Parser(Language(tspython.language()))
    return _parser


def _docstring(body, data: bytes):
    """Return the body's leading docstring text, or None."""
    if not body.children:
        return None
    first = body.children[0]
    if (
        first.type == "expression_statement"
        and first.children
        and first.children[0].type == "string"
    ):
        return data[first.start_byte:first.end_byte].decode("utf-8", "ignore")
    return None


def _collect_edits(node, data: bytes, keep: set[str], edits: list, cls: str | None = None):
    """Collapse every function body except the ones named in `keep`.

    `cls` is the enclosing class, so a method can be kept by its qualified
    name (`ConfigError.__init__`). That keeps one class's constructor without
    keeping every `__init__` in the request.
    """
    for child in node.children:
        if child.type == "class_definition":
            name_node = child.child_by_field_name("name")
            cname = _text(name_node, data) if name_node is not None else None
            _collect_edits(child, data, keep, edits, cname or cls)
            continue
        if child.type == "function_definition":
            name_node = child.child_by_field_name("name")
            name = _text(name_node, data) if name_node else ""
            if name in keep or (cls and f"{cls}.{name}" in keep):
                # keep this one in full, but still collapse nested functions
                _collect_edits(child, data, keep, edits, cls)
                continue
            body = child.child_by_field_name("body")
            if body is not None:
                indent = " " * body.start_point[1]
                doc = _docstring(body, data)
                repl = f"{doc}\n{indent}..." if doc else "..."
                edits.append((body.start_byte, body.end_byte, repl.encode("utf-8")))
            continue  # do NOT recurse into a collapsed function
        _collect_edits(child, data, keep, edits, cls)


def collapse_python(source: str, keep: set[str] | None = None) -> str:
    """Replace Python function/method bodies with '...', keeping signatures.

    `keep` is a set of function names to leave fully intact.
    Non-Python or unparseable text is returned unchanged.
    """
    keep = keep or set()
    try:
        parser = _get_parser()
    except Exception:  # tree-sitter not installed -> no-op
        return source

    data = source.encode("utf-8")
    tree = parser.parse(data)
    edits: list = []
    _collect_edits(tree.root_node, data, keep, edits)
    if not edits:
        return source
    # apply edits back-to-front so earlier byte offsets stay valid
    for start, end, repl in sorted(edits, key=lambda e: e[0], reverse=True):
        data = data[:start] + repl + data[end:]
    return data.decode("utf-8", "ignore")


# ---- phase 2: focus detection + call graph --------------------------------
#
# Instead of collapsing *every* function, keep the "focus" functions (the ones
# the task is about) AND the functions they call, up to a few hops. Everything
# else is collapsed to a signature. Focus is taken from ctx["focus"] and from
# function names the user mentions in plain-text messages.


def _defined_functions(source: str) -> set[str]:
    try:
        parser = _get_parser()
    except Exception:
        return set()
    data = source.encode("utf-8")
    tree = parser.parse(data)
    names: set[str] = set()

    def walk(node):
        for child in node.children:
            if child.type == "function_definition":
                nn = child.child_by_field_name("name")
                if nn is not None:
                    names.add(data[nn.start_byte:nn.end_byte].decode("utf-8", "ignore"))
            walk(child)

    walk(tree.root_node)
    return names


def _text(node, data: bytes) -> str:
    return data[node.start_byte:node.end_byte].decode("utf-8", "ignore")


def _defined_classes(source: str) -> dict[str, set[str]]:
    """Map each class defined in `source` to the method names it defines."""
    try:
        parser = _get_parser()
    except Exception:
        return {}
    data = source.encode("utf-8")
    tree = parser.parse(data)
    classes: dict[str, set[str]] = {}

    def walk(node, cls: str | None = None):
        for child in node.children:
            if child.type == "class_definition":
                nn = child.child_by_field_name("name")
                cname = _text(nn, data) if nn is not None else None
                if cname:
                    classes.setdefault(cname, set())
                walk(child, cname or cls)
                continue
            if child.type == "function_definition" and cls:
                nn = child.child_by_field_name("name")
                if nn is not None:
                    classes.setdefault(cls, set()).add(_text(nn, data))
            walk(child, cls)

    walk(tree.root_node)
    return classes


def _class_bases(source: str) -> dict[str, tuple[str, ...]]:
    """Map each class to the names of its direct base classes.

    Taken from the class header, so a base defined in another file is still
    named here and `super()` can be resolved against the merged symbol set.
    """
    try:
        parser = _get_parser()
    except Exception:
        return {}
    data = source.encode("utf-8")
    tree = parser.parse(data)
    bases: dict[str, tuple[str, ...]] = {}

    def walk(node):
        for child in node.children:
            if child.type == "class_definition":
                nn = child.child_by_field_name("name")
                args = child.child_by_field_name("superclasses")
                names: list[str] = []
                if args is not None:
                    for arg in args.children:
                        if arg.type == "identifier":
                            names.append(_text(arg, data))
                        elif arg.type == "attribute":  # mod.Base -> "Base"
                            attr = arg.child_by_field_name("attribute")
                            if attr is not None:
                                names.append(_text(attr, data))
                if nn is not None:
                    bases[_text(nn, data)] = tuple(names)
            walk(child)

    walk(tree.root_node)
    return bases


def _super_method(fn_node, data: bytes) -> str:
    """`super().foo()` -> "foo", otherwise ""."""
    if fn_node is None or fn_node.type != "attribute":
        return ""
    obj = fn_node.child_by_field_name("object")
    if obj is None or obj.type != "call":
        return ""
    inner = obj.child_by_field_name("function")
    if inner is None or _text(inner, data) != "super":
        return ""
    attr = fn_node.child_by_field_name("attribute")
    return _text(attr, data) if attr is not None else ""


def _constructor(cls: str) -> str:
    """The qualified name of a class's constructor."""
    return f"{cls}.__init__"


def _symbols(source: str) -> set[str]:
    """Every name the call graph can resolve in `source`.

    Functions, classes, and the qualified constructor of each class that
    defines one. Classes are included so that instantiating a class
    (`raise ConfigError(...)`) resolves to a known symbol instead of being
    dropped as an unresolvable call.
    """
    classes = _defined_classes(source)
    names = _defined_functions(source) | set(classes)
    names |= {f"{cls}.{m}" for cls, methods in classes.items() for m in methods}
    return names


def _callee_name(fn_node, data: bytes) -> str:
    """Name of the function being called, or "" if it cannot be resolved.

    Attribute calls (`obj.method()`) are matched by their bare method name,
    which is an approximation: it can link to a same-named function elsewhere
    in the file. It errs towards keeping too much rather than too little.

    `super().method()` returns "" here: it dispatches to the *base class*, so
    treating it as a call to a same-named function in this file would produce
    a false edge (notably `__init__` appearing to call itself). It is resolved
    separately, against the class's declared bases, by `_super_method`.
    """
    if fn_node is None:
        return ""
    if fn_node.type == "identifier":
        return _text(fn_node, data)
    if fn_node.type == "attribute":  # obj.method(...) -> "method"
        obj = fn_node.child_by_field_name("object")
        if obj is not None and obj.type == "call":
            inner = obj.child_by_field_name("function")
            if inner is not None and _text(inner, data) == "super":
                return ""
        attr = fn_node.child_by_field_name("attribute")
        if attr is not None:
            return _text(attr, data)
    return ""


def build_call_graph(source: str, known: set[str] | None = None) -> dict[str, set[str]]:
    """Map each function defined in `source` to the functions it calls.

    A call is only recorded when its target is a *known* function. By default
    "known" means defined in this same source. Pass `known` to resolve calls
    against a wider set — e.g. every function in the whole request — so that a
    dependency living in another file is still recorded.
    """
    try:
        parser = _get_parser()
    except Exception:
        return {}
    data = source.encode("utf-8")
    tree = parser.parse(data)
    defined = _defined_functions(source)
    classes = _defined_classes(source)
    bases = _class_bases(source)
    if known is None:
        known = _symbols(source)
    graph: dict[str, set[str]] = {name: set() for name in defined}

    def calls_in(node, cls: str | None = None) -> set[str]:
        found: set[str] = set()

        def w(n):
            if n.type == "call":
                fn = n.child_by_field_name("function")
                method = _super_method(fn, data) if cls else ""
                if method:
                    # super().foo() dispatches to a base class, which may be
                    # declared in another file; the merged symbol set says
                    # which of the declared bases actually defines it.
                    for base in bases.get(cls, ()):
                        qualified = f"{base}.{method}"
                        if qualified in known:
                            found.add(qualified)
                else:
                    name = _callee_name(fn, data)
                    if name in known:
                        found.add(name)
            for c in n.children:
                w(c)

        w(node)
        return found

    def walk(node, cls: str | None = None):
        for child in node.children:
            if child.type == "class_definition":
                nn = child.child_by_field_name("name")
                cname = _text(nn, data) if nn is not None else None
                # Instantiating a class runs its constructor, so an edge to
                # the class leads on to that constructor's body.
                if cname and "__init__" in classes.get(cname, set()):
                    graph.setdefault(cname, set()).add(_constructor(cname))
                walk(child, cname or cls)
                continue
            if child.type == "function_definition":
                nn = child.child_by_field_name("name")
                body = child.child_by_field_name("body")
                if nn is not None and body is not None:
                    caller = data[nn.start_byte:nn.end_byte].decode("utf-8", "ignore")
                    # Drop self-edges: recursion adds nothing to focus
                    # expansion, since the caller is already in the set.
                    edges = {c for c in calls_in(body, cls) if c != caller}
                    graph.setdefault(caller, set()).update(edges)
                    if cls:
                        # Also under the qualified name, so expanding from one
                        # class's method does not pull in every same-named
                        # method in the request.
                        qualified = f"{cls}.{caller}"
                        graph.setdefault(qualified, set()).update(edges - {qualified})
            walk(child, cls)

    walk(tree.root_node)
    return graph


def expand_focus(focus: set[str], graph: dict[str, set[str]], hops: int = 2) -> set[str]:
    """BFS from focus over the call graph, up to `hops` levels."""
    keep = set(focus)
    frontier = set(focus)
    for _ in range(max(0, hops)):
        nxt: set[str] = set()
        for f in frontier:
            nxt |= graph.get(f, set())
        new = nxt - keep
        if not new:
            break
        keep |= new
        frontier = new
    return keep


def _looks_like_code(content: str) -> bool:
    return bool(_defined_functions(content))


def merge_call_graphs(sources: list[str]) -> tuple[dict[str, set[str]], set[str]]:
    """Build ONE call graph spanning several sources.

    A request usually arrives as several messages, one per file. Building a
    graph per source would miss any call that crosses a file boundary, so the
    dependency of a focus function living in another file would be collapsed
    away — dropping context the task actually needs. Resolving every source
    against the union of all defined names keeps those edges.
    """
    defined_all: set[str] = set()
    for src in sources:
        defined_all |= _symbols(src)

    graph: dict[str, set[str]] = {}
    for src in sources:
        for caller, callees in build_call_graph(src, known=defined_all).items():
            graph.setdefault(caller, set()).update(callees)
    return graph, defined_all


def _count_messages(messages: list) -> int:
    return sum(
        count_tokens(m["content"])
        for m in messages
        if isinstance(m.get("content"), str)
    )


class CodeTrimmer:
    """Implements the Trimmer contract from gateway/interfaces.py."""

    def trim(self, messages: list, token_budget: int, ctx: dict | None = None):
        before = _count_messages(messages)
        if before <= token_budget:
            return messages, {
                "tokens_before": before,
                "tokens_after": before,
                "tokens_saved": 0,
                "trimmed": False,
            }

        ctx = ctx or {}
        hops = int(ctx.get("hops", 2))

        # Parse each message once: its set of defined functions doubles as the
        # "is this code?" test, so we avoid re-parsing the same text repeatedly.
        contents = [
            m["content"] if isinstance(m.get("content"), str) else None
            for m in messages
        ]
        defined_per = [_symbols(c) if c is not None else set() for c in contents]

        # ONE graph across every code message, so a call that crosses a file
        # boundary is still an edge.
        code_sources = [c for c, d in zip(contents, defined_per) if c is not None and d]
        graph, defined_all = merge_call_graphs(code_sources)

        # focus = explicit ctx focus + function names mentioned in plain-text
        # (non-code) messages
        focus_names = set(ctx.get("focus", []))
        for c, d in zip(contents, defined_per):
            if c is not None and not d:
                focus_names |= {w for w in _WORD.findall(c) if w in defined_all}

        # Expand once, globally; with no focus at all everything collapses.
        focus = focus_names & defined_all
        keep_all = expand_focus(focus, graph, hops) if focus else set()

        # Keeping a class means keeping its constructor: the task may well be
        # about what the constructor does with its arguments. Added after the
        # hop budget is spent, so a class reached on the last hop still brings
        # its constructor, then expanded again for what the constructor calls.
        ctors = {_constructor(c) for c in keep_all} & defined_all
        if ctors:
            keep_all |= expand_focus(ctors, graph, hops)

        trimmed = []
        for m, content, defined in zip(messages, contents, defined_per):
            if content is not None:
                m = {**m, "content": collapse_python(content, keep_all & defined)}
            trimmed.append(m)

        after = _count_messages(trimmed)
        return trimmed, {
            "tokens_before": before,
            "tokens_after": after,
            "tokens_saved": before - after,
            "trimmed": True,
        }
