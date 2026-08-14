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

        keep = set((ctx or {}).get("keep", []))
        trimmed = []
        for m in messages:
            content = m.get("content")
            if isinstance(content, str):
                m = {**m, "content": collapse_python(content, keep)}
            trimmed.append(m)

        after = _count_messages(trimmed)
        return trimmed, {
            "tokens_before": before,
            "tokens_after": after,
            "tokens_saved": before - after,
            "trimmed": True,
        }
