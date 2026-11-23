"""Application services, including atomic CSV import and reporting"""

import csv
from dataclasses import dataclass
from pathlib import Path

from .domain import (
    Kind,
    NewTransaction,
    Transaction,
    ValidationError,
    build_transaction,
)
from .repository import Repository

CSV_FIELDS = ["date", "kind", "amount", "category", "description"]

REQUIRED_CSV_FIELDS = ["date", "kind", "amount", "category"]


@dataclass(frozen=True)
class Summary:
    income_cents: int
    expense_cents: int
    by_category: dict[str, int]

    @property
    def balance_cents(self) -> int:
        return self.income_cents - self.expense_cents


def import_csv(repository: Repository, path: Path) -> list[Transaction]:
    # Validate header + parse all rows BEFORE touching the repository,
    # so a bad file never leaves partial state behind (atomicity).
    try:
        with path.open(newline="", encoding="utf-8-sig") as source:
            reader = csv.DictReader(source, strict=True)
            if reader.fieldnames != CSV_FIELDS:
                raise ValidationError(
                    f"Expected columns {CSV_FIELDS}, got {reader.fieldnames}"
                )

            new_transactions: list[NewTransaction] = []
            errors: list[str] = []
            for line_no, row in enumerate(reader, start=2):
                try:
                    new_transactions.append(_parse_row(row))
                except ValidationError as exc:
                    errors.append(f"line {line_no}: {exc}")

            if errors:
                raise ValidationError("; ".join(errors))

        # All rows valid -> persist atomically.
        return repository.add_many(new_transactions)

    except csv.Error as exc:
        raise ValidationError(f"Malformed CSV: {exc}") from exc


def _parse_row(row: dict[str, str | None]) -> NewTransaction:
    missing = [
        field
        for field in REQUIRED_CSV_FIELDS
        if not (row.get(field) or "").strip()
    ]
    if missing:
        raise ValidationError(f"missing required field(s): {', '.join(missing)}")

    # Delegate date/amount/kind/category/description validation to the domain.
    return build_transaction(
        (row.get("date") or "").strip(),
        (row.get("kind") or "").strip(),
        (row.get("amount") or "").strip(),
        (row.get("category") or "").strip(),
        (row.get("description") or "").strip(),
    )


def summarize(transactions: list[Transaction]) -> Summary:
    income = 0
    expense = 0
    by_category: dict[str, int] = {}
    for txn in transactions:
        if txn.kind is Kind.INCOME:
            income += txn.amount_cents
        else:
            expense += txn.amount_cents
        by_category[txn.category] = by_category.get(txn.category, 0) + txn.amount_cents
    return Summary(income_cents=income, expense_cents=expense, by_category=by_category)