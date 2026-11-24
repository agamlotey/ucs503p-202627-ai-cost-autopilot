"""Keep every report's shared parts identical.

The proposal, the prototype report and the final report all carry the same
eight UML diagrams, the same Gantt chart and the same test-case table. Holding
one copy per report invites them to drift, and reaching across folders with
`../docs/...` leaves a report folder that cannot be built or zipped on its own.

So: `report-common/` is the single source, and this script copies it into each
report folder, which stays self-contained. The copies are generated, so edit
the originals in `report-common/` and run this again.

    python report-common/sync.py
"""
from __future__ import annotations

import os
import shutil

from make_testcases import main as generate_test_cases

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

REPORTS = (
    "project-proposal",
    "project-report-prototype-stage",
    "project-report-final",
)

FRAGMENTS = ("diagrams.tex", "gantt.tex", "test-cases.tex")

BANNER = ("% GENERATED COPY -- do not edit.\n"
          "% Source: report-common/{name}; run `python report-common/sync.py`.\n")


def sync_one(report: str) -> tuple[int, int]:
    dest = os.path.join(ROOT, report)
    if not os.path.isdir(dest):
        raise SystemExit(f"no such report folder: {report}")

    figures = os.path.join(dest, "figures")
    os.makedirs(figures, exist_ok=True)
    copied = 0
    for fn in sorted(os.listdir(os.path.join(HERE, "figures"))):
        if fn.endswith(".pdf"):
            shutil.copy2(os.path.join(HERE, "figures", fn), os.path.join(figures, fn))
            copied += 1

    written = 0
    for name in FRAGMENTS:
        src = os.path.join(HERE, name)
        if not os.path.exists(src):
            continue
        with open(src, encoding="utf-8") as fh:
            body = fh.read()
        with open(os.path.join(dest, name), "w", encoding="utf-8") as fh:
            fh.write(BANNER.format(name=name) + body)
        written += 1
    return copied, written


def main() -> None:
    generate_test_cases()
    for report in REPORTS:
        figures, fragments = sync_one(report)
        print(f"  {report}: {figures} figures, {fragments} shared sections")


if __name__ == "__main__":
    main()
