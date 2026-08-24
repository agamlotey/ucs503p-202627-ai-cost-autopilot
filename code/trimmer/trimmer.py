"""
Compiler-Aware Trimmer  —  OWNER: Agam

v1 (prototype): parse Python with tree-sitter and collapse function/method
bodies to their signatures (keeping the docstring), so the model still sees the
*shape* of the code without paying for every line. Token savings measured with
tiktoken.

Later: dependency graph (keep the focus + its direct deps in full), more
languages. See trimmer/README.md.

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


def _collect_edits(node, data: bytes, keep: set[str], edits: list):
    for child in node.children:
        if child.type == "function_definition":
            name_node = child.child_by_field_name("name")
            name = (
                data[name_node.start_byte:name_node.end_byte].decode("utf-8", "ignore")
                if name_node else ""
            )
            if name in keep:
                # keep this one in full, but still collapse nested functions
                _collect_edits(child, data, keep, edits)
                continue
            body = child.child_by_field_name("body")
            if body is not None:
                indent = " " * body.start_point[1]
                doc = _docstring(body, data)
                repl = f"{doc}\n{indent}..." if doc else "..."
                edits.append((body.start_byte, body.end_byte, repl.encode("utf-8")))
            # do NOT recurse into a collapsed function
        else:
            _collect_edits(child, data, keep, edits)


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


def _callee_name(fn_node, data: bytes) -> str:
    if fn_node is None:
        return ""
    if fn_node.type == "identifier":
        return data[fn_node.start_byte:fn_node.end_byte].decode("utf-8", "ignore")
    if fn_node.type == "attribute":  # obj.method(...) -> "method"
        attr = fn_node.child_by_field_name("attribute")
        if attr is not None:
            return data[attr.start_byte:attr.end_byte].decode("utf-8", "ignore")
    return ""


def build_call_graph(source: str) -> dict[str, set[str]]:
    """Map each function name to the set of (known) functions it calls."""
    try:
        parser = _get_parser()
    except Exception:
        return {}
    data = source.encode("utf-8")
    tree = parser.parse(data)
    defined = _defined_functions(source)
    graph: dict[str, set[str]] = {name: set() for name in defined}

    def calls_in(node) -> set[str]:
        found: set[str] = set()

        def w(n):
            if n.type == "call":
                name = _callee_name(n.child_by_field_name("function"), data)
                if name in defined:
                    found.add(name)
            for c in n.children:
                w(c)

        w(node)
        return found

    def walk(node):
        for child in node.children:
            if child.type == "function_definition":
                nn = child.child_by_field_name("name")
                body = child.child_by_field_name("body")
                if nn is not None and body is not None:
                    caller = data[nn.start_byte:nn.end_byte].decode("utf-8", "ignore")
                    graph.setdefault(caller, set()).update(calls_in(body))
            walk(child)

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


def _keep_for(code: str, focus_names: set[str], hops: int) -> set[str]:
    """Which functions to leave fully intact in this code block."""
    defined = _defined_functions(code)
    if not defined:
        return set()
    focus = (focus_names & defined)
    if not focus:
        return set()  # no focus here -> collapse everything (v1 behaviour)
    return expand_focus(focus, build_call_graph(code), hops) & defined


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

        # every function defined anywhere in the request
        defined_all: set[str] = set()
        for m in messages:
            c = m.get("content")
            if isinstance(c, str) and _looks_like_code(c):
                defined_all |= _defined_functions(c)

        # focus = explicit ctx focus + function names mentioned in plain-text
        # (non-code) messages
        focus_names = set(ctx.get("focus", []))
        for m in messages:
            c = m.get("content")
            if isinstance(c, str) and not _looks_like_code(c):
                focus_names |= {w for w in _WORD.findall(c) if w in defined_all}

        trimmed = []
        for m in messages:
            content = m.get("content")
            if isinstance(content, str):
                keep = _keep_for(content, focus_names, hops)
                m = {**m, "content": collapse_python(content, keep)}
            trimmed.append(m)

        after = _count_messages(trimmed)
        return trimmed, {
            "tokens_before": before,
            "tokens_after": after,
            "tokens_saved": before - after,
            "trimmed": True,
        }
