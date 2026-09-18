import sqlite3
import os
import pandas as pd


DB = "db/nifty100.db"


def test_database_exists():
    """Check that SQLite database exists."""
    assert os.path.exists(DB)


def test_required_tables_exist():
    """Check that all 12 required tables exist."""

    required_tables = {
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "analysis",
        "documents",
        "prosandcons",
        "sectors",
        "market_cap",
        "stock_prices",
        "financial_ratios",
        "peer_groups",
    }

    conn = sqlite3.connect(DB)

    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }

    conn.close()

    assert required_tables.issubset(tables)


def test_companies_count():
    """Check that companies table contains 92 companies."""

    conn = sqlite3.connect(DB)

    count = conn.execute(
        "SELECT COUNT(*) FROM companies"
    ).fetchone()[0]

    conn.close()

    assert count == 92


def test_tables_have_data():
    """Check that every required table contains data."""

    required_tables = [
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "analysis",
        "documents",
        "prosandcons",
        "sectors",
        "market_cap",
        "stock_prices",
        "financial_ratios",
        "peer_groups",
    ]

    conn = sqlite3.connect(DB)

    for table in required_tables:

        count = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        assert count > 0, f"{table} is empty"

    conn.close()


def test_dq_report_exists():
    """Check that DQ report was generated."""

    assert os.path.exists("output/dq_report.csv")


def test_dq_report_readable():
    """Check that DQ report can be read."""

    df = pd.read_csv("output/dq_report.csv")

    assert len(df) == 12
    assert "table" in df.columns
    assert "rows" in df.columns
    assert "columns" in df.columns
    assert "missing_values" in df.columns