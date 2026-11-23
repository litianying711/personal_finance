# Personal Finance Tracker

A command-line personal finance tracker backed by SQLite.

## Install

```bash
python -m pip install -e ".[dev]"
```

## Usage

```bash
personal-finance --db finance.db add income 2500.00 Salary --date 2025-01-31
personal-finance --db finance.db add expense 42.50 Food --description "Weekly groceries"
personal-finance --db finance.db list --month 2025-01
personal-finance --db finance.db summary --month 2025-01
personal-finance --db finance.db import transactions.csv
```

The CSV importer expects the columns `date,kind,amount,category,description`.
Dates use `YYYY-MM-DD`; transaction kinds are `income` and `expense`.

The database defaults to `~/.personal_finance/finance.db`. Set
`FINANCE_TRACKER_DB` or pass `--db` to choose another location.

## Tests

```bash
python -m pytest
```
