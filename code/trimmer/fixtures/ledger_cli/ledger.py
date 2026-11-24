"""The ledger itself."""

from money import add_amounts
from validators import validate


class Ledger:
    """A named list of validated entries."""

    def __init__(self, name, entries=None):
        self.name = name
        self.entries = list(entries or [])
        self.closed = False

    def add(self, entry, row=None):
        """Validate an entry and append it."""
        if self.closed:
            raise RuntimeError("ledger is closed")
        validate(entry, row)
        self.entries.append(entry)
        return len(self.entries)

    def extend(self, entries):
        for number, entry in enumerate(entries, start=1):
            self.add(entry, number)
        return len(self.entries)

    def total(self):
        return add_amounts(entry["amount"] for entry in self.entries)

    def close(self):
        self.closed = True
        return self.total()
