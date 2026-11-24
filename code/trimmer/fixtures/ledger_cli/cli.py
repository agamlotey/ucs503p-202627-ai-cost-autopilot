"""Command line entry point."""

from errors import LedgerError
from report import biggest_category, render
from storage import load


def main(lines, argv=None):
    """Summarise a CSV ledger, or report why it could not be read."""
    argv = list(argv or [])
    try:
        ledger = load(lines, name=_name(argv))
    except LedgerError as exc:
        return f"error: {exc}"
    if "--top" in argv:
        return biggest_category(ledger) or "nothing recorded"
    return render(ledger)


def _name(argv):
    for index, arg in enumerate(argv):
        if arg == "--name" and index + 1 < len(argv):
            return argv[index + 1]
    return "ledger"
