from datetime import date

import pytest

from finance_tracker.domain import (
    Kind,
    ValidationError,
    build_transaction,
    clean_text,
    format_money,
    parse_amount,
    parse_date,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("2026-01-02", date(2026, 1, 2)), (" 2024-02-29 ", date(2024, 2, 29))],
)
def test_parse_date_accepts_iso_dates(value, expected):
    assert parse_date(value) == expected


@pytest.mark.parametrize("value", ["", "2024-2-01", "2023-02-29", "not-a-date"])
def test_parse_date_rejects_invalid_dates(value):
    with pytest.raises(ValidationError):
        parse_date(value)


@pytest.mark.parametrize(("value", "expected"), [("12", 1200), ("12.3", 1230), ("0.01", 1)])
def test_parse_amount_converts_dollars_to_cents(value, expected):
    assert parse_amount(value) == expected


@pytest.mark.parametrize("value", ["0", "-1.00", "1.001", "NaN", "abc"])
def test_parse_amount_rejects_invalid_amounts(value):
    with pytest.raises(ValidationError):
        parse_amount(value)


def test_clean_text_collapses_whitespace_and_allows_optional_empty_value():
    assert clean_text("  groceries \n and   food ", "category") == "groceries and food"
    assert clean_text(" \n ", "description", required=False) == ""


@pytest.mark.parametrize(
    ("value", "required"),
    [("", True), ("x" * 201, False)],
)
def test_clean_text_rejects_missing_or_oversized_values(value, required):
    with pytest.raises(ValidationError):
        clean_text(value, "category", required=required)


def test_build_transaction_normalizes_kind_and_fields():
    item = build_transaction("2025-03-04", " INCOME ", "10.25", "  Salary  ", "  March pay ")

    assert item.occurred_on == date(2025, 3, 4)
    assert item.kind is Kind.INCOME
    assert item.amount_cents == 1025
    assert item.category == "Salary"
    assert item.description == "March pay"


@pytest.mark.parametrize(("cents", "expected"), [(0, "$0.00"), (123456, "$1,234.56"), (-5, "-$0.05")])
def test_format_money(cents, expected):
    assert format_money(cents) == expected
