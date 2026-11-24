"""
Does a real model still fix the bug when it only sees the trimmed context?

Every other measurement here counts tokens. Tokens cannot tell a good
reduction from a cheaper wrong answer, so this one asks the question that
matters: give a real model the same task twice, once with the whole project
and once with only what the trimmer kept, and judge both by the project's own
tests.

The experiment:

  1. Copy `ledger_cli` and inject one real bug.
  2. Check the project's tests now fail, so the task is not already done.
  3. Ask the model to fix it, with FULL context and with TRIMMED context.
  4. Apply each answer to a fresh copy of the broken project.
  5. Run the project's own 13 tests against each.

The injected bug is deliberately NOT in the function the task names. The task
says "fix parse_row", but the fault is in `LedgerError._describe`, two steps
away through a constructor and a `super()` call. That is the case the trimmer
used to get wrong: before class instantiation and `super()` were resolved, the
trimmed context did not contain the broken code at all, so the model could not
have fixed it however good it was.

Costs real money: two completions per task on the configured provider, a few
cents in all. Needs PROVIDER_API_KEY set and MOCK_PROVIDER off; with the mock
provider it refuses to run, because a canned reply proves nothing.

Run from code/:
    python -m trimmer.benchmark.agent_run
    python -m trimmer.benchmark.agent_run --model gpt-4o-mini --keep
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass

from gateway import config, provider
from trimmer.fixtures.loader import as_messages, project_files
from trimmer.trimmer import CodeTrimmer, count_tokens

FIXTURE = "ledger_cli"
# A real coding agent is given the failing test, not just a wish. Without that
# signal the model patches whatever the task names and never looks further,
# which tells you nothing about the context it was given.
TASK = (
    "A row that fails to parse no longer says which row it was. Running the "
    "project's tests gives:\n\n"
    "    FAILED tests/test_ledger.py::test_cli_reports_errors_with_the_row_number\n"
    "    out = main([\"date,category,amount,note\", \"2026-13-01,food,10,bad month\"])\n"
    "    assert \"row 2\" in out\n"
    "    AssertionError: assert 'row 2' in 'error: could not read date: \\'2026-13-01\\''\n\n"
    "The row number reaches parse_row correctly, so look at what happens to it "
    "after that. Find the cause and fix it. Do not change the tests."
)

# One realistic regression: the row number is dropped from the message. The
# project's own test_cli_reports_errors_with_the_row_number catches it.
BUG_FILE = "errors.py"
BUG_FIND = """    def _describe(self):
        if self.row is None:
            return self.message
        return f"{self.message} (row {self.row})\""""
BUG_REPLACE = """    def _describe(self):
        return self.message"""

INSTRUCTIONS = (
    "You are fixing a bug in a Python project.\n\n"
    "Task: {task}\n\n"
    "Reply with the COMPLETE new contents of every file you change, and nothing "
    "else. Use exactly this format for each file, including the '# file:' line:\n\n"
    "```python\n# file: <relative/path.py>\n<the whole file>\n```\n\n"
    "Some files are shown with function bodies replaced by `...` to save space. "
    "That is elision, not code. Leave those `...` exactly as they are: they will "
    "be restored for you. Only write real code for the function you are fixing.\n\n"
    "Change as few files as possible. Do not explain."
)


# List price per million tokens, for a rough cost line. Unknown models fall
# back to the cheapest entry, so the figure is an underestimate, never a scare.
PRICES = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
}
MODEL = {"name": "gpt-4o-mini"}


def _price() -> tuple[float, float]:
    return PRICES.get(MODEL["name"], (0.15, 0.60))


@dataclass
class Outcome:
    label: str
    sent_tokens: int
    prompt_tokens: int
    completion_tokens: int
    files_changed: tuple[str, ...]
    passed: int
    failed: int
    ok: bool
    stub_echoes: tuple[str, ...] = ()

    @property
    def cost(self) -> float:
        price_in, price_out = _price()
        return self.prompt_tokens * price_in / 1e6 + self.completion_tokens * price_out / 1e6


def broken_project(dest: str) -> None:
    """Write the fixture into `dest` with the bug applied."""
    os.makedirs(dest, exist_ok=True)
    for rel, source in project_files(FIXTURE, include_tests=True):
        path = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if rel == BUG_FILE:
            if BUG_FIND not in source:
                raise SystemExit(f"the fixture changed: {BUG_FILE} no longer contains the bug site")
            source = source.replace(BUG_FIND, BUG_REPLACE, 1)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(source)


def run_tests(root: str) -> tuple[int, int]:
    """(passed, failed) from the project's own suite."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", os.path.join(root, "tests")],
        capture_output=True, text=True, cwd=root,
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONPATH": root},
    )
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", tail)) else 0
    failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", tail)) else 0
    if not passed and not failed and proc.returncode != 0:
        failed = 1  # a collection error is a failure too
    return passed, failed


def broken_sources() -> list[tuple[str, str]]:
    """The fixture's source files (no tests) with the bug applied."""
    out = []
    for rel, source in project_files(FIXTURE):
        if rel == BUG_FILE:
            source = source.replace(BUG_FIND, BUG_REPLACE, 1)
        out.append((rel, source))
    return out


def full_messages() -> list[dict]:
    messages = [{"role": "user", "content": INSTRUCTIONS.format(task=TASK)}]
    for rel, source in broken_sources():
        messages.append({"role": "user", "content": f"# file: {rel}\n{source}"})
    return messages


def trimmed_messages() -> list[dict]:
    """The same request after the trimmer, with the task text it keys on."""
    messages = [{"role": "user", "content": TASK}]
    for rel, source in broken_sources():
        messages.append({"role": "user", "content": f"# file: {rel}\n{source}"})
    trimmed, _stats = CodeTrimmer().trim(messages, token_budget=0)
    trimmed[0] = {"role": "user", "content": INSTRUCTIONS.format(task=TASK)}
    return trimmed


def collapsed_bodies(source: str) -> set[str]:
    """Functions in `source` whose body is just an ellipsis."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = [n for n in node.body
                if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                        and isinstance(n.value.value, str))]
        if len(body) == 1 and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant) and body[0].value.value is Ellipsis:
            found.add(node.name)
    return found


def _function_spans(source: str) -> dict[str, tuple[int, int, bool]]:
    """Qualified function name -> (first line, last line, body is elided)."""
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    spans: dict[str, tuple[int, int, bool]] = {}

    def walk(node, prefix=""):
        for child in getattr(node, "body", []):
            if isinstance(child, ast.ClassDef):
                walk(child, f"{prefix}{child.name}.")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = [n for n in child.body
                        if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                                and isinstance(n.value.value, str))]
                elided = (len(body) == 1 and isinstance(body[0], ast.Expr)
                          and isinstance(body[0].value, ast.Constant)
                          and body[0].value.value is Ellipsis)
                spans[f"{prefix}{child.name}"] = (child.lineno, child.end_lineno, elided)
                walk(child, prefix)

    walk(tree)
    return spans


def reexpand(returned: str, original: str) -> tuple[str, list[str]]:
    """Put back the bodies the trimmer elided.

    The gateway is what replaced those bodies with `...`, so the gateway is
    what can restore them. Without this step a model answering with whole
    files hands the elision back as if it were code, and applying that answer
    deletes working functions. The model's own edits are untouched.
    """
    want = _function_spans(returned)
    have = _function_spans(original)
    out_lines = returned.split("\n")
    orig_lines = original.split("\n")
    restored = []
    # bottom-up so earlier line numbers stay valid
    for name, (start, end, elided) in sorted(want.items(), key=lambda kv: -kv[1][0]):
        if not elided or name not in have:
            continue
        o_start, o_end, o_elided = have[name]
        if o_elided:
            continue
        out_lines[start - 1:end] = orig_lines[o_start - 1:o_end]
        restored.append(name)
    return "\n".join(out_lines), sorted(restored)


def extract_files(reply: str) -> dict[str, str]:
    """'# file: path' blocks from the answer."""
    found: dict[str, str] = {}
    for block in re.findall(r"```(?:python)?\s*\n(.*?)```", reply, re.S):
        m = re.match(r"\s*#\s*file:\s*(\S+)\s*\n(.*)", block, re.S)
        if m:
            found[m.group(1).strip()] = m.group(2)
    return found


def extract_edits(reply: str) -> list[tuple[str, str, str]]:
    """(path, search, replace) for each edit block in the answer."""
    pattern = re.compile(
        r"#\s*file:\s*(\S+)\s*\n<<<<<<<\s*SEARCH\s*\n(.*?)\n?=======\s*\n(.*?)\n?>>>>>>>\s*REPLACE",
        re.S)
    return [(m.group(1).strip(), m.group(2), m.group(3)) for m in pattern.finditer(reply)]


def ask(messages: list[dict], model: str) -> dict:
    return asyncio.run(provider.forward({"model": model, "messages": messages}))


def attempt(label: str, messages: list[dict], model: str, workdir: str,
            trial: int = 1) -> Outcome:
    sent = sum(count_tokens(m["content"]) for m in messages)
    response = ask(messages, model)
    reply = response["choices"][0]["message"]["content"]
    usage = response.get("usage", {})

    root = os.path.join(workdir, f"t{trial}-" + label.lower().replace(" ", "-"))
    broken_project(root)
    original = dict(broken_sources())
    applied, notes = [], []
    for rel, content in extract_files(reply).items():
        path = os.path.join(root, os.path.normpath(rel).lstrip("/"))
        if not os.path.abspath(path).startswith(os.path.abspath(root)):
            continue  # never write outside the scratch copy
        if rel not in original:
            notes.append(f"{rel}: not a file in this project")
            continue
        content, restored = reexpand(content, original[rel])
        if restored:
            notes.append(f"{rel}: restored {len(restored)} elided body(ies): "
                         f"{', '.join(restored[:3])}{'...' if len(restored) > 3 else ''}")
        still_elided = collapsed_bodies(content) - collapsed_bodies(original[rel])
        if still_elided:
            notes.append(f"{rel}: REJECTED, still elided after re-expansion")
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        applied.append(rel)

    passed, failed = run_tests(root)
    return Outcome(label, sent, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
                   tuple(sorted(set(applied))), passed, failed, failed == 0 and passed > 0,
                   tuple(notes))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default=config.DEFAULT_MODEL)
    ap.add_argument("--keep", action="store_true", help="keep the scratch copies")
    ap.add_argument("--trials", type=int, default=1,
                    help="repeat both conditions N times; a single run proves nothing, "
                         "because the model is not deterministic")
    args = ap.parse_args()

    if config.MOCK_PROVIDER or not config.PROVIDER_API_KEY:
        raise SystemExit(
            "This benchmark needs a real provider: a canned reply cannot fix a bug.\n"
            "Set PROVIDER_API_KEY in code/.env and MOCK_PROVIDER=0.")

    MODEL["name"] = args.model
    workdir = tempfile.mkdtemp(prefix="agent-run-")
    try:
        control = os.path.join(workdir, "control")
        broken_project(control)
        passed, failed = run_tests(control)
        print(f"\nFixture: {FIXTURE}   Task: \"{TASK}\"")
        print(f"Bug injected in {BUG_FILE} (LedgerError._describe), which the task does not name.")
        print(f"Before any fix: {passed} passed, {failed} failed  "
              f"({'good, there is something to fix' if failed else 'PROBLEM: nothing fails'})")
        if not failed:
            raise SystemExit("the injected bug no longer breaks the suite; update BUG_FIND")

        tally = {"Full context": [], "Trimmed context": []}
        spend = 0.0
        for trial in range(1, args.trials + 1):
            results = [
                attempt("Full context", full_messages(), args.model, workdir, trial),
                attempt("Trimmed context", trimmed_messages(), args.model, workdir, trial),
            ]
            if trial == 1:
                print(f"\nModel: {args.model}\n")
                print(f"  {'trial':>5}  {'condition':<17} {'sent':>7} {'reply':>6} "
                      f"{'tests':>20}  {'cost':>9}")
            for r in results:
                tally[r.label].append(r.ok)
                spend += r.cost
                verdict = f"{r.passed} passed, {r.failed} failed"
                print(f"  {trial:>5}  {r.label:<17} {r.sent_tokens:>7,} "
                      f"{r.completion_tokens:>6,} {verdict:>20}  ${r.cost:>8.5f}")
                for note in r.stub_echoes:
                    print(f"  {'':>5}  {'':<17} note: {note}")

        full_ok, trimmed_ok = sum(tally["Full context"]), sum(tally["Trimmed context"])
        n = args.trials
        sent_full = sum(count_tokens(m["content"]) for m in full_messages())
        sent_trim = sum(count_tokens(m["content"]) for m in trimmed_messages())
        saved = 100 * (sent_full - sent_trim) / sent_full if sent_full else 0

        print(f"\n  Full context    : fixed it in {full_ok} of {n} trials "
              f"({sent_full:,} tokens sent)")
        print(f"  Trimmed context : fixed it in {trimmed_ok} of {n} trials "
              f"({sent_trim:,} tokens sent, {saved:.1f}% fewer)")
        if trimmed_ok >= full_ok:
            print("  Trimming did not cost correctness on this task: the smaller "
                  "context did at least as well.")
        else:
            print("  The trimmed context did worse. Check the notes above for whether "
                  "that was missing context or an unapplied edit.")
        if n < 3:
            print("  Note: the model is not deterministic. Use --trials 5 or more "
                  "before quoting these numbers.")

        print(f"\n  Total spend: ${spend:.5f}")
        if args.keep:
            print(f"  Scratch copies kept in {workdir}")
    finally:
        if not args.keep:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    main()
