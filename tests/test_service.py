import pytest

from finance_tracker.domain import Kind, ValidationError, build_transaction
from finance_tracker.repository import Repository
from finance_tracker.service import import_csv, summarize


@pytest.fixture
def repository(tmp_path):
    return Repository(tmp_path / "finance.db")


def test_import_csv_handles_bom_and_quoted_fields(repository, tmp_path):
    csv_file = tmp_path / "transactions.csv"
    csv_file.write_text(
        "\ufeffdate,kind,amount,category,description\n"
        '2025-01-01,income,1000,Salary,"January, pay"\n'
        "2025-01-02,expense,25.50,Food,Lunch\n",
        encoding="utf-8",
    )

    imported = import_csv(repository, csv_file)

    assert [item.amount_cents for item in imported] == [100000, 2550]
    assert imported[0].description == "January, pay"
    assert len(repository.list()) == 2


def test_import_csv_rejects_invalid_rows_without_partial_writes(repository, tmp_path):
    repository.add(build_transaction("2025-01-01", "income", "10", "Salary"))
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text(
        "date,kind,amount,category,description\n"
        "2025-01-02,expense,5,Food,Valid row\n"
        "2025-02-30,expense,7,Food,Invalid date\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="line 3"):
        import_csv(repository, csv_file)

    assert len(repository.list()) == 1


def test_import_csv_rejects_wrong_header(repository, tmp_path):
    csv_file = tmp_path / "wrong-header.csv"
    csv_file.write_text("date,amount\n2025-01-01,10\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="Expected columns"):
        import_csv(repository, csv_file)

    assert repository.list() == []


def test_summarize_totals_and_category_amounts():
    transactions = [
        build_transaction("2025-01-01", "income", "2500", "Salary"),
        build_transaction("2025-01-02", "expense", "50", "Food"),
        build_transaction("2025-01-03", "expense", "25", "Food"),
    ]

    summary = summarize(
        [
            type("TransactionRecord", (), {
                "kind": item.kind,
                "amount_cents": item.amount_cents,
                "category": item.category,
            })()
            for item in transactions
        ]
    )

    assert summary.income_cents == 250000
    assert summary.expense_cents == 7500
    assert summary.balance_cents == 242500
    assert summary.by_category == {"Salary": 250000, "Food": 7500}


def test_summarize_uses_transaction_kinds():
    summary = summarize(
        [
            type("TransactionRecord", (), {
                "kind": Kind.EXPENSE,
                "amount_cents": 100,
                "category": "Transport",
            })()
        ]
    )

    assert summary.income_cents == 0
    assert summary.expense_cents == 100
