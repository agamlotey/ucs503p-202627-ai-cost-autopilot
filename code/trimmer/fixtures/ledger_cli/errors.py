"""Errors raised by the ledger."""


class LedgerError(Exception):
    """Base class for every ledger failure."""

    def __init__(self, message, row=None):
        self.message = message
        self.row = row
        super().__init__(self._describe())

    def _describe(self):
        if self.row is None:
            return self.message
        return f"{self.message} (row {self.row})"


class ParseError(LedgerError):
    """A cell could not be read."""

    def __init__(self, field, value, row=None):
        self.field = field
        self.value = value
        super().__init__(f"could not read {field}: {value!r}", row)


class AmountError(LedgerError):
    """An amount was zero or negative."""

    def __init__(self, amount, row=None):
        self.amount = amount
        super().__init__(f"amount must be positive, got {amount}", row)


class UnknownCategory(LedgerError):
    """A category is not in the allowed set."""

    def __init__(self, name, known, row=None):
        self.name = name
        self.known = sorted(known)
        super().__init__(f"unknown category {name!r}", row)
