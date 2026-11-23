"""Domain types and input validation"""
from dataclasses import dataclass
from enum import Enum
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from unittest import expectedFailure


class ValidationError(ValueError):
    """Raise when transaction input is invalid"""

class Kind(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"

@dataclass(frozen=True)
class NewTransaction:
    occurred_on: date
    kind: Kind
    amount_cents: int
    category: str
    description: str = ""

@dataclass(frozen=True)
class Transaction:
    id: int
    occurred_on: date
    kind: Kind
    amount_cents: int
    category: str
    description: str
    needs_review: bool

MAX_AMOUNT_CENTS=9_223_372_036_854_775_807

def parse_date(value: str) -> date:
    cleaned = value.strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", cleaned):
        raise ValidationError(f"invalidate date {value!r}; expected yyyy-mm-dd")
    try:
        return date.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValidationError(f"invalidate date {value!r}; expected yyyy-mm-dd") from exc

def parse_amount(value: str) -> int:
    try:
        amount = Decimal(value.strip())
        if not amount.is_finite() or amount <= 0:
            raise ValidationError("amount must be a positive number")
        rounded = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, AttributeError) as exc:
        raise ValidationError(f"invalidate amount {value!r}") from exc
    if rounded != amount:
        raise ValidationError("amount must at most 2 decimal places")
    cents = int(rounded * 100)
    if cents > MAX_AMOUNT_CENTS:
        raise ValidationError("amount too large")
    return cents
def clean_text(value: str, field: str, *, required: bool = True) -> str:
    cleaned = " ".join((value or "").split())
    if required and not cleaned:
        raise ValidationError(f"{field} is required")
    if len(cleaned) > 200:
        raise ValidationError(f"{field} must be at most 200 characters long")
    return cleaned

def build_transaction(date_value: str, kind_value: str, amount: str, category: str, description: str = "") -> NewTransaction:
    try:
        kind = Kind(kind_value.strip().lower())
    except (ValueError, AttributeError) as exc:
        raise ValidationError("kind must be 'income' or 'expense") from exc
    return NewTransaction(
        occurred_on = parse_date(date_value),
        kind = kind,
        amount_cents=parse_amount(amount),
        category = clean_text(category, "category"),
        description = clean_text(description, "description", required=False),
    )

def format_money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}${cents // 100:,}.{cents % 100:02d}"



