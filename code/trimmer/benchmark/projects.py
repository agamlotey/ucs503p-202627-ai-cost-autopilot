"""
Does the trimmer's saving hold on a second codebase?

`baselines.py` answers "is compiler-aware trimming better than the cheap
tricks" on one project. That is not enough on its own: the trimmer keys on
code shape (call graph, class structure, how much a function pulls in), so a
single fixture can only show that it worked once. This module runs the same
measurement across every fixture project and several tasks each, and reports
them side by side.

The two projects are deliberately unalike:

  notes_api   a request-handling service; one class defines a constructor
  ledger_cli  a command line tool: a four-deep exception hierarchy and a
              stateful Ledger class, five constructors in all, so it
              exercises the class-instantiation edges that notes_api barely
              touches. It ships its own passing test suite.

For each task it also checks **context sufficiency**: every function a correct
patch has to read is still present in full after trimming. A saving that drops
something the fix needs is not a saving, it is a wrong answer that happens to
be cheaper, and tokens alone cannot tell the two apart.

Run from code/:
    python -m trimmer.benchmark.projects
    python -m trimmer.benchmark.projects --markdown      # table for the report
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field

from trimmer.benchmark.baselines import _all_compile, _function_bodies, _without_header
from trimmer.fixtures.loader import as_messages, project_files
from trimmer.trimmer import CodeTrimmer, count_tokens


@dataclass(frozen=True)
class Task:
    """A task, and the functions a correct patch has to be able to read.

    `needs` is written by hand from the fix itself, not from the trimmer's
    output, so it is a real check and not a restatement of what the trimmer
    happened to keep.
    """
    fixture: str
    task: str
    needs: tuple[str, ...]


TASKS: tuple[Task, ...] = (
    Task("notes_api", "fix create_note", ("create_note", "validate_note")),
    Task("notes_api", "fix delete_note", ("delete_note",)),
    Task("ledger_cli", "fix parse_row",
         ("parse_row", "split_row", "parse_date", "parse_amount", "normalise")),
    Task("ledger_cli", "fix validate so the error names the field",
         ("validate", "check_fields", "check_category")),
    Task("ledger_cli", "fix render so totals line up",
         ("render", "by_category", "format_amount")),
)


@dataclass
class Measurement:
    fixture: str
    task: str
    raw_tokens: int
    trimmed_tokens: int
    kept: int
    total: int
    valid: bool
    missing: tuple[str, ...] = field(default=())

    @property
    def saved_pct(self) -> float:
        if not self.raw_tokens:
            return 0.0
        return 100 * (self.raw_tokens - self.trimmed_tokens) / self.raw_tokens

    @property
    def sufficient(self) -> bool:
        return not self.missing


def measure(task: Task, hops: int = 2) -> Measurement:
    raw = [src for _rel, src in project_files(task.fixture)]
    trimmed_msgs, _stats = CodeTrimmer().trim(
        as_messages(task.task, task.fixture), token_budget=0, ctx={"hops": hops}
    )
    trimmed = [_without_header(m["content"]) for m in trimmed_msgs[1:]]
    full, collapsed = _function_bodies(trimmed)
    return Measurement(
        fixture=task.fixture,
        task=task.task,
        raw_tokens=sum(count_tokens(s) for s in raw),
        trimmed_tokens=sum(count_tokens(s) for s in trimmed),
        kept=len(full),
        total=len(full) + len(collapsed),
        valid=_all_compile(trimmed),
        missing=tuple(n for n in task.needs if n not in full),
    )


def run(hops: int = 2) -> list[Measurement]:
    return [measure(t, hops) for t in TASKS]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _print(results: list[Measurement], markdown: bool) -> None:
    if markdown:
        print("| Project | Task | Tokens | Saved | Kept | Valid | Context |")
        print("|---|---|---:|---:|---:|---|---|")
        for r in results:
            print(f"| `{r.fixture}` | {r.task} | {r.trimmed_tokens:,} of {r.raw_tokens:,} "
                  f"| {r.saved_pct:.1f}% | {r.kept} of {r.total} "
                  f"| {'yes' if r.valid else '**no**'} "
                  f"| {'complete' if r.sufficient else '**missing ' + ', '.join(r.missing) + '**'} |")
    else:
        width = max(len(r.task) for r in results) if results else 10
        print(f"\n  {'project':<11} {'task':<{width}} {'tokens':>13} {'saved':>7} "
              f"{'kept':>8}  output\n")
        for r in results:
            note = "valid" if r.valid else "BROKEN"
            note += ", context complete" if r.sufficient else f", MISSING {', '.join(r.missing)}"
            print(f"  {r.fixture:<11} {r.task:<{width}} "
                  f"{r.trimmed_tokens:>5,} of {r.raw_tokens:<5,} {r.saved_pct:>6.1f}% "
                  f"{r.kept:>3} of {r.total:<3} {note}")

    for fixture in dict.fromkeys(r.fixture for r in results):
        rows = [r for r in results if r.fixture == fixture]
        line = (f"mean saving on {fixture}: {_mean([r.saved_pct for r in rows]):.1f}% "
                f"over {len(rows)} tasks")
        print(f"\n  {line}" if not markdown else f"\n{line}")

    broken = [r for r in results if not r.valid or not r.sufficient]
    if broken:
        print("\n  WARNING: some runs lost context or broke the code (see above)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hops", type=int, default=2)
    ap.add_argument("--markdown", action="store_true", help="table for the report")
    args = ap.parse_args()
    _print(run(args.hops), args.markdown)


if __name__ == "__main__":
    main()
