"""Command-line interface"""

import argparse
import os
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

from .domain import *
from .repository import Repository
from .service import import_csv, summarize

DEFAULT_DB = Path(os.environ.get("FINANCE_TRACKER_DB", "~/.personal_finance/finance.db"))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="finance-tracker", description="Finance Tracker")
    result.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite database path")
    commands = result.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="record a transaction")
    add.add_argument("kind", choices=[kind.value for kind in Kind])
    add.add_argument("amount", help="positive amount, e.g.12.45")
    add.add_argument("category")
    add.add_argument("--description", default="")
    add.add_argument("--date", default=date.today().isoformat(), dest="occurred_on")

    listing = commands.add_parser("list", help="list transactions")
    _filters(listing)

    summary = commands.add_parser("summary", help="summarize transactions")
    _filters(summary)

    importing = commands.add_parser("import", help="atomically import a csv file")
    importing.add_argument("file", type=Path, help="path to csv file")
    return result


def _filters(command: argparse.ArgumentParser) -> None:
    command.add_argument("--month", help="YYYY-MM")
    command.add_argument("--kind", choices=[kind.value for kind in Kind])
    command.add_argument("--category")
    command.add_argument(
        "--review-only",
        action="store_true",
        dest="review_only",
        help="only show transactions flagged for review",
    )


def _validated_month(value: str | None) -> str | None:
    if value and not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", value):
        raise ValidationError("month must be YYYY-MM")
    return value


def _selected(repository: Repository, args: argparse.Namespace):
    return repository.list(
        month=_validated_month(args.month),
        kind=Kind(args.kind) if args.kind else None,
        category=args.category,
        review_only=getattr(args, "review_only", False),
    )


def run(args: argparse.Namespace) -> int:
    repository = Repository(args.db)
    if args.command == "add":
        item = build_transaction(
            args.occurred_on, args.kind, args.amount, args.category, args.description
        )
        saved = repository.add(item)
        suffix = " [REVIEW: possible duplication]" if saved.needs_review else ""
        print(f"Added transaction {saved.id}{suffix}")
    elif args.command == "import":
        saved = import_csv(repository, args.file)
        flagged = sum(item.needs_review for item in saved)
        print(f"Imported {len(saved)} transaction(s); {flagged} flagged for review")
    elif args.command == "list":
        items = _selected(repository, args)
        if not items:
            print("No transactions found.")
        for item in items:
            marker = " REVIEW" if item.needs_review else ""
            description = f" | {item.description}" if item.description else ""
            print(
                f"{item.id:>4}| {item.occurred_on} | {item.kind.value:<7}| "
                f"{format_money(item.amount_cents):>12} | {item.category}{description}{marker}"
            )
    elif args.command == "summary":
        report = summarize(_selected(repository, args))
        print(f"Income: {format_money(report.income_cents)}")
        print(f"Expenses: {format_money(report.expense_cents)}")
        print(f"Balance:  {format_money(report.balance_cents)}")
        if report.by_category:
            print("By Category (income positive, expenses negative)")
            for category, cents in report.by_category.items():
                print(f"  {category}: {format_money(cents)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(parser().parse_args(argv))
    except (ValidationError, OSError, sqlite3.Error) as err:
        print(f"error: {err}", file=sys.stderr)
        return 2