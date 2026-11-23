from finance_tracker.cli import main


def test_cli_add_and_summary_use_selected_database(tmp_path, capsys):
    database = tmp_path / "cli.db"

    assert main(
        [
            "--db",
            str(database),
            "add",
            "income",
            "1200.00",
            "Salary",
            "--date",
            "2025-06-01",
            "--description",
            "Monthly pay",
        ]
    ) == 0
    assert "Added transaction 1" in capsys.readouterr().out

    assert main(["--db", str(database), "summary"]) == 0
    output = capsys.readouterr().out
    assert "Income: $1,200.00" in output
    assert "Expenses: $0.00" in output
    assert "Balance:  $1,200.00" in output


def test_cli_reports_validation_errors_without_traceback(tmp_path, capsys):
    result = main(
        [
            "--db",
            str(tmp_path / "cli.db"),
            "add",
            "expense",
            "0",
            "Food",
            "--date",
            "2025-01-01",
        ]
    )

    captured = capsys.readouterr()
    assert result == 2
    assert "error:" in captured.err
    assert captured.out == ""
