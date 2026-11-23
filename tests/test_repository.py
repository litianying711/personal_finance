from datetime import date

import pytest

from finance_tracker.domain import Kind, NewTransaction
from finance_tracker.repository import Repository


@pytest.fixture
def repository(tmp_path):
    return Repository(tmp_path / "finance.db")


def transaction(
    *,
    occurred_on=date(2025, 1, 10),
    kind=Kind.EXPENSE,
    amount_cents=1250,
    category="Food",
    description="Lunch",
):
    return NewTransaction(occurred_on, kind, amount_cents, category, description)


def test_add_persists_and_returns_transaction(repository):
    saved = repository.add(transaction())

    assert saved.id == 1
    assert saved.occurred_on == date(2025, 1, 10)
    assert saved.kind is Kind.EXPENSE
    assert saved.amount_cents == 1250
    assert saved.category == "Food"
    assert saved.description == "Lunch"
    assert not saved.needs_review
    assert repository.list() == [saved]


def test_add_flags_duplicate_ignoring_description_case_and_whitespace(repository):
    first = repository.add(transaction(description="Coffee shop"))
    duplicate = repository.add(
        transaction(category="Dining", description="  COFFEE   SHOP ")
    )
    different_date = repository.add(
        transaction(occurred_on=date(2025, 1, 11), description="Coffee shop")
    )

    assert not first.needs_review
    assert duplicate.needs_review
    assert not different_date.needs_review
    assert [item.id for item in repository.list(review_only=True)] == [duplicate.id]


def test_list_applies_filters_and_sorts_newest_first(repository):
    older = repository.add(transaction(occurred_on=date(2025, 1, 2)))
    newer_income = repository.add(
        transaction(
            occurred_on=date(2025, 2, 3),
            kind=Kind.INCOME,
            category="Salary",
        )
    )
    newest = repository.add(
        transaction(occurred_on=date(2025, 2, 10), category="FOOD")
    )

    assert [item.id for item in repository.list()] == [newest.id, newer_income.id, older.id]
    assert repository.list(month="2025-02", kind=Kind.EXPENSE, category="food") == [newest]
    assert repository.list(month="2025-02", kind=Kind.INCOME) == [newer_income]


def test_add_many_is_atomic_when_a_row_violates_database_constraints(repository):
    existing = repository.add(transaction())
    items = [
        transaction(occurred_on=date(2025, 1, 11)),
        transaction(occurred_on=date(2025, 1, 12), kind="transfer"),
    ]

    with pytest.raises(Exception):
        repository.add_many(items)

    assert repository.list() == [existing]
