"""SQLite persistence for transactions."""

import sqlite3
from collections.abc import Iterable, Sequence
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from .domain import Kind, NewTransaction, Transaction


class Repository:
    def __init__(self, database: Path) -> None:
        self.database = database.expanduser()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY,
                    occurred_on TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK(kind IN ('income', 'expense')),
                    amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0),
                    category TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    normalized_description TEXT NOT NULL,
                    needs_review INTEGER NOT NULL DEFAULT 0
                        CHECK (needs_review IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_transactions_date "
                "ON transactions(occurred_on)"
            )

    @contextmanager
    def batch(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _normalized(description: str) -> str:
        return " ".join(description.casefold().split())

    def add(
        self,
        item: NewTransaction,
        connection: sqlite3.Connection | None = None,
    ) -> Transaction:
        if connection is None:
            with self.batch() as owned:
                return self.add(item, owned)
        return self._insert(item, connection)

    def add_many(self, items: Iterable[NewTransaction]) -> list[Transaction]:
        items = list(items)
        if not items:
            return []
        with self.batch() as connection:
            return [self._insert(item, connection) for item in items]

    def _insert(
        self, item: NewTransaction, connection: sqlite3.Connection
    ) -> Transaction:
        normalized = self._normalized(item.description)
        duplicate = connection.execute(
            """SELECT 1 FROM transactions
               WHERE occurred_on = ? AND kind = ? AND amount_cents = ?
                 AND normalized_description = ? LIMIT 1""",
            (
                item.occurred_on.isoformat(),
                item.kind.value if isinstance(item.kind, Kind) else item.kind,
                item.amount_cents,
                normalized,
            ),
        ).fetchone()
        needs_review = duplicate is not None
        cursor = connection.execute(
            """INSERT INTO transactions
                (occurred_on, kind, amount_cents, category, description,
                 normalized_description, needs_review)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                item.occurred_on.isoformat(),
                item.kind.value if isinstance(item.kind, Kind) else item.kind,
                item.amount_cents,
                item.category,
                item.description,
                normalized,
                int(needs_review),
            ),
        )
        return Transaction(
            cursor.lastrowid,
            item.occurred_on,
            item.kind,
            item.amount_cents,
            item.category,
            item.description,
            needs_review,
        )

    def list(
        self,
        *,
        month: str | None = None,
        kind: Kind | None = None,
        category: str | None = None,
        review_only: bool = False,
    ) -> list[Transaction]:
        clauses, parameters = [], []
        if month:
            clauses.append("substr(occurred_on, 1, 7) = ?")
            parameters.append(month)
        if kind:
            clauses.append("kind = ?")
            parameters.append(kind.value if isinstance(kind, Kind) else kind)
        if category:
            clauses.append("lower(category) = lower(?)")
            parameters.append(category)
        if review_only:
            clauses.append("needs_review = 1")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM transactions" + where
                + " ORDER BY occurred_on DESC, id DESC",
                parameters,
            ).fetchall()
        return [self._to_transaction(row) for row in rows]

    @staticmethod
    def _to_transaction(row: sqlite3.Row) -> Transaction:
        return Transaction(
            row["id"],
            date.fromisoformat(row["occurred_on"]),
            Kind(row["kind"]),
            row["amount_cents"],
            row["category"],
            row["description"],
            bool(row["needs_review"]),
        )