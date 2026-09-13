"""
Trimmer vs. simple baselines, on a realistic fixture.

Answers one question: does compiler-aware trimming beat the obvious cheap
tricks, and does it stay correct while doing it? Every variant is measured on
exactly the same text (the fixture's file contents) and every result is checked
to still compile, because a saving that breaks the code is not a saving.

Variants:
  raw               the files untouched (the control)
  strip-indent      remove indentation and blank lines  (cheap, breaks Python)
  strip-comments    remove comments and docstrings      (the simplest safe trick)
  collapse-all      collapse every function body         (valid, but drops the focus)
  trimmer           keep the focus + its callees, collapse the rest

Run from code/:
    python -m trimmer.benchmark.baselines
    python -m trimmer.benchmark.baselines --task "fix create_note" --fixture notes_api
    python -m trimmer.benchmark.baselines --markdown      # table for the docs
"""
from __future__ import annotations

import argparse
import ast
import io
import re
import tokenize
from dataclasses import dataclass

from trimmer.fixtures.loader import as_messages, project_files
from trimmer.trimmer import CodeTrimmer, collapse_python, count_tokens


# ---- baselines --------------------------------------------------------------

def strip_indentation(source: str) -> str:
    """Drop leading whitespace and blank lines. Saves tokens, breaks Python."""
    return "\n".join(line.strip() for line in source.split("\n") if line.strip())


def strip_comments_and_docstrings(source: str) -> str:
    """Remove comments and docstrings, keeping the code valid.

    A docstring that is a body's only statement is replaced with `pass`;
    deleting it outright would leave an empty body, and a baseline that breaks
    the code is not one anybody would use.
    """
    lines = source.split("\n")
    drop: set[int] = set()
    add_pass: dict[int, str] = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.Module, ast.FunctionDef,
                                 ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        body = node.body
        first = body[0] if body else None
        if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            drop.update(range(first.lineno - 1, first.end_lineno))
            if len(body) == 1:
                add_pass[first.lineno - 1] = " " * first.col_offset + "pass"
    kept = [add_pass.get(i, line) for i, line in enumerate(lines)
            if i not in drop or i in add_pass]
    source = "\n".join(kept)
    toks = [t for t in tokenize.generate_tokens(io.StringIO(source).readline)
            if t.type != tokenize.COMMENT]
    source = tokenize.untokenize(toks)
    source = re.sub(r"\n\s*\n+", "\n\n", source)
    return re.sub(r"\n[ \t]*(?=\n)", "\n", source)


def _without_header(content: str) -> str:
    """as_messages() prefixes each file with a '# file: <path>' line. Strip it
    so the trimmer is measured on the same text as every baseline."""
    first, _, rest = content.partition("\n")
    return rest if first.startswith("# file: ") else content


# ---- measurement ------------------------------------------------------------

@dataclass
class Result:
    name: str
    tokens: int
    saved_pct: float
    valid: bool
    note: str = ""


def _all_compile(sources: list[str]) -> bool:
    try:
        for src in sources:
            compile(src, "<fixture>", "exec")
        return True
    except SyntaxError:
        return False


def _function_bodies(sources: list[str]) -> tuple[set[str], set[str]]:
    """(functions kept in full, functions collapsed to `...`)."""
    full: set[str] = set()
    collapsed: set[str] = set()
    for src in sources:
        for node in ast.walk(ast.parse(src)):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = [s for s in node.body
                    if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
                            and isinstance(s.value.value, str))]
            stub = (len(body) == 1 and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and body[0].value.value is Ellipsis)
            (collapsed if stub else full).add(node.name)
    return full, collapsed


def run(task: str = "fix create_note", fixture: str = "notes_api", hops: int = 2) -> list[Result]:
    raw = [src for _rel, src in project_files(fixture)]
    base = sum(count_tokens(s) for s in raw)

    # token_budget=0 forces the trimmer to run: this measures what it does, not
    # whether the gateway's budget would have triggered it on this request.
    trimmed, _stats = CodeTrimmer().trim(as_messages(task, fixture), token_budget=0,
                                         ctx={"hops": hops})
    trimmer_out = [_without_header(m["content"]) for m in trimmed[1:]]
    full, collapsed = _function_bodies(trimmer_out)

    variants = [
        ("raw (no gateway)", raw, ""),
        ("strip indentation + blank lines", [strip_indentation(s) for s in raw], ""),
        ("strip comments + docstrings", [strip_comments_and_docstrings(s) for s in raw], ""),
        ("collapse every function body", [collapse_python(s) for s in raw], "drops the focus"),
        (f"trimmer (focus + callees, {hops} hops)", trimmer_out,
         f"{len(full)} of {len(full) + len(collapsed)} functions kept in full"),
    ]
    results = []
    for name, sources, note in variants:
        tokens = sum(count_tokens(s) for s in sources)
        results.append(Result(name, tokens, 100 * (base - tokens) / base,
                              _all_compile(sources), note))
    return results


def _print(results: list[Result], task: str, fixture: str, markdown: bool) -> None:
    if markdown:
        print(f"Task: \"{task}\" on `{fixture}`\n")
        print("| Variant | Tokens | Saved | Output |")
        print("|---|---:|---:|---|")
        for r in results:
            out = ("valid" if r.valid else "**broken**") + (f", {r.note}" if r.note else "")
            print(f"| {r.name} | {r.tokens:,} | {r.saved_pct:.1f}% | {out} |")
        return
    print(f"\nTask: \"{task}\"   fixture: {fixture}\n")
    print(f"  {'variant':<38}{'tokens':>8}{'saved':>9}   output")
    for r in results:
        out = ("valid" if r.valid else "BROKEN") + (f", {r.note}" if r.note else "")
        print(f"  {r.name:<38}{r.tokens:>8,}{r.saved_pct:>8.1f}%   {out}")
    print("\nEvery variant is measured on the same file contents and checked to"
          "\nstill compile. Tokens: tiktoken cl100k_base.\n")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--task", default="fix create_note")
    ap.add_argument("--fixture", default="notes_api")
    ap.add_argument("--hops", type=int, default=2)
    ap.add_argument("--markdown", action="store_true", help="print a Markdown table")
    args = ap.parse_args(argv)
    _print(run(args.task, args.fixture, args.hops), args.task, args.fixture, args.markdown)


if __name__ == "__main__":
    main()
