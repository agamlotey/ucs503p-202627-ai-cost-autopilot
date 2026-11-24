"""The ledger project's own tests.

Not collected by the gateway's suite (see code/pytest.ini `testpaths`): they
exist so a patch produced by a coding agent can be checked against the
project's own definition of correct.
"""
import pytest

from categories import aliases_for, normalise
from cli import main
from dates import is_leap, parse_date
from errors import AmountError, ParseError, UnknownCategory
from money import format_amount, parse_amount
from parser import parse_row, parse_rows
from report import biggest_category, by_category, by_month
from storage import dump, load
from validators import validate

ROWS = [
    "date,category,amount,note",
    "2026-03-09,groceries,1200.50,weekly shop",
    "2026-03-11,cab,240,airport",
    "2026-04-01,rent,18000,april",
]


def test_parse_amount_handles_decimals_and_separators():
    assert parse_amount("12.50") == 1250
    assert parse_amount("1,200") == 120000
    assert parse_amount("7") == 700


def test_parse_amount_rejects_rubbish():
    with pytest.raises(ParseError):
        parse_amount("abc")
    with pytest.raises(ParseError):
        parse_amount("1.2.3")


def test_format_amount_round_trips():
    assert format_amount(parse_amount("12.50")) == "12.50"
    assert format_amount(-1250) == "-12.50"


def test_parse_date_validates_the_calendar():
    assert parse_date("2026-03-09") == (2026, 3, 9)
    with pytest.raises(ParseError):
        parse_date("2026-02-30")
    with pytest.raises(ParseError):
        parse_date("not-a-date")


def test_leap_years():
    assert is_leap(2024) and is_leap(2000)
    assert not is_leap(1900) and not is_leap(2026)


def test_categories_resolve_aliases():
    assert normalise("groceries") == "food"
    assert normalise("") == "misc"
    assert aliases_for("travel") == ["cab", "flight"]
    with pytest.raises(UnknownCategory):
        normalise("crypto")


def test_parse_row_builds_an_entry():
    entry = parse_row("2026-03-09,dining,45.25,lunch")
    assert entry == {
        "date": (2026, 3, 9),
        "category": "food",
        "amount": 4525,
        "note": "lunch",
    }


def test_parse_rows_skips_the_header():
    assert len(parse_rows(ROWS)) == 3


def test_validate_rejects_a_non_positive_amount():
    with pytest.raises(AmountError):
        validate({"date": (2026, 3, 9), "category": "food", "amount": 0})


def test_report_totals():
    ledger = load(ROWS, name="march")
    assert by_category(ledger)["food"] == 120050
    assert by_month(ledger) == {"2026-03": 144050, "2026-04": 1800000}
    assert biggest_category(ledger) == "rent"
    assert ledger.total() == 1944050


def test_dump_round_trips_through_load():
    ledger = load(ROWS)
    again = load(dump(ledger))
    assert again.total() == ledger.total()


def test_cli_reports_errors_with_the_row_number():
    out = main(["date,category,amount,note", "2026-13-01,food,10,bad month"])
    assert out.startswith("error:")
    assert "row 2" in out


def test_cli_renders_a_summary():
    out = main(ROWS, ["--name", "march"])
    assert "ledger: march" in out
    assert "rent" in out
