import sqlite3
import re
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

FAILURE_FILE = OUTPUT_DIR / "validation_failures.csv"


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

failures = []


def add_failure(rule, severity, table, company_id="", year="", details=""):
    failures.append(
        {
            "rule": rule,
            "severity": severity,
            "table": table,
            "company_id": company_id,
            "year": year,
            "details": details,
        }
    )


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return [row[0] for row in rows]


def load_table(conn, table):
    return pd.read_sql_query(f'SELECT * FROM "{table}"', conn)


def find_column(df, candidates):
    """
    Find a column using several possible names.
    """
    lookup = {str(c).lower().strip(): c for c in df.columns}

    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    return None


def numeric_series(df, column):
    return pd.to_numeric(df[column], errors="coerce")


# ---------------------------------------------------------
# DQ-01
# Company Primary Key Uniqueness
# ---------------------------------------------------------

def dq01(companies):
    col = find_column(companies, ["id", "company_id"])

    if col is None:
        add_failure(
            "DQ-01",
            "CRITICAL",
            "companies",
            details="Company ID column not found"
        )
        return

    duplicates = companies[
        companies[col].duplicated(keep=False)
    ]

    for _, row in duplicates.iterrows():
        add_failure(
            "DQ-01",
            "CRITICAL",
            "companies",
            company_id=str(row[col]),
            details="Duplicate company primary key"
        )

    if len(duplicates) == 0:
        print("[PASS] DQ-01 Company PK uniqueness")


# ---------------------------------------------------------
# DQ-02
# Annual Primary Key Uniqueness
# ---------------------------------------------------------

def dq02(conn):
    for table in ["profitandloss", "balancesheet", "cashflow"]:
        if table not in get_tables(conn):
            continue

        df = load_table(conn, table)

        company_col = find_column(df, ["company_id"])
        year_col = find_column(df, ["year"])

        if company_col is None or year_col is None:
            add_failure(
                "DQ-02",
                "CRITICAL",
                table,
                details="company_id/year column missing"
            )
            continue

        duplicate_mask = df.duplicated(
            subset=[company_col, year_col],
            keep=False
        )

        duplicates = df[duplicate_mask]

        for _, row in duplicates.iterrows():
            add_failure(
                "DQ-02",
                "CRITICAL",
                table,
                company_id=str(row[company_col]),
                year=str(row[year_col]),
                details="Duplicate company/year primary key"
            )

        if len(duplicates) == 0:
            print(f"[PASS] DQ-02 {table} uniqueness")


# ---------------------------------------------------------
# DQ-03
# Foreign Key Integrity
# ---------------------------------------------------------

def dq03(conn, companies):
    company_col = find_column(companies, ["id", "company_id"])

    if company_col is None:
        add_failure(
            "DQ-03",
            "CRITICAL",
            "companies",
            details="Company ID column missing"
        )
        return

    valid_ids = set(
        companies[company_col]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
    )

    tables = [
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

    for table in tables:
        if table not in get_tables(conn):
            continue

        df = load_table(conn, table)
        company_col = find_column(df, ["company_id"])

        if company_col is None:
            continue

        for _, row in df.iterrows():
            value = row[company_col]

            if pd.isna(value):
                add_failure(
                    "DQ-03",
                    "CRITICAL",
                    table,
                    details="Missing company_id"
                )
                continue

            company_id = str(value).strip().upper()

            if company_id not in valid_ids:
                add_failure(
                    "DQ-03",
                    "CRITICAL",
                    table,
                    company_id=company_id,
                    details="Orphan company_id"
                )

    if not any(f["rule"] == "DQ-03" for f in failures):
        print("[PASS] DQ-03 Foreign key integrity")


# ---------------------------------------------------------
# DQ-04
# Balance Sheet Balance
# ---------------------------------------------------------

def dq04(bs):
    assets_col = find_column(bs, ["total_assets"])
    liabilities_col = find_column(bs, ["total_liabilities"])
    company_col = find_column(bs, ["company_id"])
    year_col = find_column(bs, ["year"])

    if not assets_col or not liabilities_col:
        add_failure(
            "DQ-04",
            "WARNING",
            "balancesheet",
            details="Required balance sheet columns missing"
        )
        return

    assets = pd.to_numeric(bs[assets_col], errors="coerce")
    liabilities = pd.to_numeric(bs[liabilities_col], errors="coerce")

    valid = assets.notna() & liabilities.notna() & (assets != 0)

    difference = (assets - liabilities).abs() / assets.abs()

    bad = bs[valid & (difference >= 0.01)]

    for idx, row in bad.iterrows():
        add_failure(
            "DQ-04",
            "WARNING",
            "balancesheet",
            company_id=str(row[company_col]) if company_col else "",
            year=str(row[year_col]) if year_col else "",
            details="Assets and liabilities differ by 1% or more"
        )

    print(f"[INFO] DQ-04 Balance Sheet: {len(bad)} violations")


# ---------------------------------------------------------
# DQ-05
# Operating Profit Margin Cross Check
# ---------------------------------------------------------

def dq05(pl):
    sales_col = find_column(pl, ["sales"])
    op_profit_col = find_column(pl, ["operating_profit"])
    opm_col = find_column(
        pl,
        ["opm_percentage", "opm", "operating_profit_margin"]
    )

    company_col = find_column(pl, ["company_id"])
    year_col = find_column(pl, ["year"])

    if not sales_col or not op_profit_col or not opm_col:
        add_failure(
            "DQ-05",
            "WARNING",
            "profitandloss",
            details="OPM columns missing"
        )
        return

    sales = pd.to_numeric(pl[sales_col], errors="coerce")
    op_profit = pd.to_numeric(pl[op_profit_col], errors="coerce")
    source_opm = pd.to_numeric(pl[opm_col], errors="coerce")

    calculated_opm = (op_profit / sales) * 100

    valid = (
        sales.notna()
        & op_profit.notna()
        & source_opm.notna()
        & (sales != 0)
    )

    difference = (source_opm - calculated_opm).abs()

    bad = pl[valid & (difference >= 1)]

    for idx, row in bad.iterrows():
        add_failure(
            "DQ-05",
            "WARNING",
            "profitandloss",
            company_id=str(row[company_col]) if company_col else "",
            year=str(row[year_col]) if year_col else "",
            details="Source OPM differs from calculated OPM by >= 1%"
        )

    print(f"[INFO] DQ-05 OPM cross-check: {len(bad)} violations")


# ---------------------------------------------------------
# DQ-06
# Positive Sales
# ---------------------------------------------------------

def dq06(pl):
    sales_col = find_column(pl, ["sales"])
    company_col = find_column(pl, ["company_id"])
    year_col = find_column(pl, ["year"])

    if not sales_col:
        return

    sales = pd.to_numeric(pl[sales_col], errors="coerce")

    bad = pl[sales.notna() & (sales <= 0)]

    for _, row in bad.iterrows():
        add_failure(
            "DQ-06",
            "WARNING",
            "profitandloss",
            company_id=str(row[company_col]) if company_col else "",
            year=str(row[year_col]) if year_col else "",
            details="Sales is zero or negative"
        )

    print(f"[INFO] DQ-06 Positive sales: {len(bad)} violations")


# ---------------------------------------------------------
# DQ-07
# Year Format
# ---------------------------------------------------------

def dq07(conn):
    tables = [
        "profitandloss",
        "balancesheet",
        "cashflow",
        "financial_ratios",
    ]

    pattern = re.compile(r"^\d{4}-\d{2}$")

    for table in tables:
        if table not in get_tables(conn):
            continue

        df = load_table(conn, table)
        year_col = find_column(df, ["year"])
        company_col = find_column(df, ["company_id"])

        if year_col is None:
            continue

        for _, row in df.iterrows():
            year = str(row[year_col]).strip()

            if not pattern.match(year):
                add_failure(
                    "DQ-07",
                    "CRITICAL",
                    table,
                    company_id=str(row[company_col]) if company_col else "",
                    year=year,
                    details="Year does not match YYYY-MM"
                )

    print("[INFO] DQ-07 Year format checked")


# ---------------------------------------------------------
# DQ-08
# Ticker Format
# ---------------------------------------------------------

def dq08(companies):
    col = find_column(companies, ["id", "company_id"])

    if col is None:
        return

    for _, row in companies.iterrows():
        ticker = str(row[col]).strip().upper()

        if not 2 <= len(ticker) <= 12:
            add_failure(
                "DQ-08",
                "CRITICAL",
                "companies",
                company_id=ticker,
                details="Ticker length outside 2-12 characters"
            )

    print("[INFO] DQ-08 Ticker format checked")


# ---------------------------------------------------------
# DQ-09
# Net Cash Flow Check
# ---------------------------------------------------------

def dq09(cf):
    cfo_col = find_column(
        cf,
        ["operating_activity", "cash_from_operating"]
    )

    cfi_col = find_column(
        cf,
        ["investing_activity", "cash_from_investing"]
    )

    cff_col = find_column(
        cf,
        ["financing_activity", "cash_from_financing"]
    )

    net_col = find_column(
        cf,
        ["net_cash_flow"]
    )

    company_col = find_column(cf, ["company_id"])
    year_col = find_column(cf, ["year"])

    if not all([cfo_col, cfi_col, cff_col, net_col]):
        add_failure(
            "DQ-09",
            "WARNING",
            "cashflow",
            details="Required cash flow columns missing"
        )
        return

    cfo = pd.to_numeric(cf[cfo_col], errors="coerce")
    cfi = pd.to_numeric(cf[cfi_col], errors="coerce")
    cff = pd.to_numeric(cf[cff_col], errors="coerce")
    net = pd.to_numeric(cf[net_col], errors="coerce")

    calculated = cfo + cfi + cff

    valid = (
        cfo.notna()
        & cfi.notna()
        & cff.notna()
        & net.notna()
    )

    bad = cf[valid & ((net - calculated).abs() > 10)]

    for _, row in bad.iterrows():
        add_failure(
            "DQ-09",
            "WARNING",
            "cashflow",
            company_id=str(row[company_col]) if company_col else "",
            year=str(row[year_col]) if year_col else "",
            details="Net cash flow differs from CFO + CFI + CFF by more than 10 Cr"
        )

    print(f"[INFO] DQ-09 Net cash flow: {len(bad)} violations")


# ---------------------------------------------------------
# DQ-10
# Non-negative Fixed Assets
# ---------------------------------------------------------

def dq10(bs):
    col = find_column(bs, ["fixed_assets"])
    company_col = find_column(bs, ["company_id"])
    year_col = find_column(bs, ["year"])

    if not col:
        return

    values = pd.to_numeric(bs[col], errors="coerce")
    bad = bs[values < 0]

    for _, row in bad.iterrows():
        add_failure(
            "DQ-10",
            "WARNING",
            "balancesheet",
            company_id=str(row[company_col]) if company_col else "",
            year=str(row[year_col]) if year_col else "",
            details="Negative fixed assets"
        )

    print(f"[INFO] DQ-10 Fixed assets: {len(bad)} violations")


# ---------------------------------------------------------
# DQ-11
# Tax Rate Range
# ---------------------------------------------------------

def dq11(pl):
    col = find_column(pl, ["tax_percentage", "tax_rate"])
    company_col = find_column(pl, ["company_id"])
    year_col = find_column(pl, ["year"])

    if not col:
        return

    values = pd.to_numeric(pl[col], errors="coerce")

    bad = pl[
        values.notna()
        & ((values < 0) | (values > 60))
    ]

    for _, row in bad.iterrows():
        add_failure(
            "DQ-11",
            "WARNING",
            "profitandloss",
            company_id=str(row[company_col]) if company_col else "",
            year=str(row[year_col]) if year_col else "",
            details="Tax percentage outside 0-60%"
        )

    print(f"[INFO] DQ-11 Tax rate: {len(bad)} violations")


# ---------------------------------------------------------
# DQ-12
# Dividend Payout Cap
# ---------------------------------------------------------

def dq12(pl):
    col = find_column(
        pl,
        ["dividend_payout", "dividend_payout_ratio"]
    )

    company_col = find_column(pl, ["company_id"])
    year_col = find_column(pl, ["year"])

    if not col:
        return

    values = pd.to_numeric(pl[col], errors="coerce")

    bad = pl[
        values.notna()
        & ((values < 0) | (values > 200))
    ]

    for _, row in bad.iterrows():
        add_failure(
            "DQ-12",
            "WARNING",
            "profitandloss",
            company_id=str(row[company_col]) if company_col else "",
            year=str(row[year_col]) if year_col else "",
            details="Dividend payout outside 0-200%"
        )

    print(f"[INFO] DQ-12 Dividend payout: {len(bad)} violations")


# ---------------------------------------------------------
# DQ-13
# Annual Report URL
# ---------------------------------------------------------

def dq13(documents):
    url_col = find_column(
        documents,
        ["annual_report", "annual_report_url"]
    )

    company_col = find_column(documents, ["company_id"])
    year_col = find_column(documents, ["year"])

    if not url_col:
        add_failure(
            "DQ-13",
            "WARNING",
            "documents",
            details="Annual report URL column not found"
        )
        return

    url_pattern = re.compile(r"^https?://[^\s]+", re.IGNORECASE)
    checked = 0

    for _, row in documents.iterrows():
        url = row[url_col]

        if pd.isna(url) or str(url).strip() == "":
            add_failure(
                "DQ-13",
                "WARNING",
                "documents",
                company_id=str(row[company_col]) if company_col else "",
                year=str(row[year_col]) if year_col else "",
                details="Missing annual report URL"
            )
            continue

        url_str = str(url).strip()
        checked += 1

        if not url_pattern.match(url_str):
            add_failure(
                "DQ-13",
                "WARNING",
                "documents",
                company_id=str(row[company_col]) if company_col else "",
                year=str(row[year_col]) if year_col else "",
                details="Invalid annual report URL format"
            )

    print(f"[INFO] DQ-13 URL validation checked {checked} URLs")


# ---------------------------------------------------------
# DQ-14
# EPS Sign Consistency
# ---------------------------------------------------------

def dq14(pl):
    profit_col = find_column(pl, ["net_profit"])
    eps_col = find_column(pl, ["eps"])

    company_col = find_column(pl, ["company_id"])
    year_col = find_column(pl, ["year"])

    if not profit_col or not eps_col:
        return

    profit = pd.to_numeric(pl[profit_col], errors="coerce")
    eps = pd.to_numeric(pl[eps_col], errors="coerce")

    bad = pl[
        profit.notna()
        & eps.notna()
        & (profit > 0)
        & (eps <= 0)
    ]

    for _, row in bad.iterrows():
        add_failure(
            "DQ-14",
            "WARNING",
            "profitandloss",
            company_id=str(row[company_col]) if company_col else "",
            year=str(row[year_col]) if year_col else "",
            details="Positive net profit with non-positive EPS"
        )

    print(f"[INFO] DQ-14 EPS sign: {len(bad)} violations")


# ---------------------------------------------------------
# DQ-15
# Strict Balance Sheet Equality
# ---------------------------------------------------------

def dq15(bs):
    assets_col = find_column(bs, ["total_assets"])
    liabilities_col = find_column(bs, ["total_liabilities"])

    company_col = find_column(bs, ["company_id"])
    year_col = find_column(bs, ["year"])

    if not assets_col or not liabilities_col:
        return

    assets = pd.to_numeric(bs[assets_col], errors="coerce")
    liabilities = pd.to_numeric(bs[liabilities_col], errors="coerce")

    bad = bs[
        assets.notna()
        & liabilities.notna()
        & (assets != liabilities)
    ]

    for _, row in bad.iterrows():
        add_failure(
            "DQ-15",
            "INFO",
            "balancesheet",
            company_id=str(row[company_col]) if company_col else "",
            year=str(row[year_col]) if year_col else "",
            details="Total assets and total liabilities are not exactly equal"
        )

    print(f"[INFO] DQ-15 Strict balance: {len(bad)} differences")


# ---------------------------------------------------------
# DQ-16
# Minimum Five Years Coverage
# ---------------------------------------------------------

def dq16(conn):
    for table in ["profitandloss", "balancesheet", "cashflow"]:
        if table not in get_tables(conn):
            continue

        df = load_table(conn, table)

        company_col = find_column(df, ["company_id"])
        year_col = find_column(df, ["year"])

        if not company_col or not year_col:
            continue

        coverage = (
            df.groupby(company_col)[year_col]
            .nunique()
        )

        bad = coverage[coverage < 5]

        for company_id, count in bad.items():
            add_failure(
                "DQ-16",
                "WARNING",
                table,
                company_id=str(company_id),
                details=f"Only {count} distinct years available; minimum is 5"
            )

    print("[INFO] DQ-16 Coverage checked")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print("=" * 70)
    print("NIFTY 100 DATA QUALITY VALIDATION")
    print("DQ-01 to DQ-16")
    print("=" * 70)

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    conn = get_connection()

    print("\nLoading tables...")

    companies = load_table(conn, "companies")
    pl = load_table(conn, "profitandloss")
    bs = load_table(conn, "balancesheet")
    cf = load_table(conn, "cashflow")
    documents = load_table(conn, "documents")

    print(f"[OK] Companies: {len(companies)}")
    print(f"[OK] Profit & Loss: {len(pl)}")
    print(f"[OK] Balance Sheet: {len(bs)}")
    print(f"[OK] Cash Flow: {len(cf)}")
    print(f"[OK] Documents: {len(documents)}")

    print("\nRunning DQ rules...\n")

    dq01(companies)
    dq02(conn)
    dq03(conn, companies)
    dq04(bs)
    dq05(pl)
    dq06(pl)
    dq07(conn)
    dq08(companies)
    dq09(cf)
    dq10(bs)
    dq11(pl)
    dq12(pl)
    dq13(documents)
    dq14(pl)
    dq15(bs)
    dq16(conn)

    conn.close()

    # -----------------------------------------------------
    # WRITE FAILURE REPORT
    # -----------------------------------------------------

    report = pd.DataFrame(
        failures,
        columns=[
            "rule",
            "severity",
            "table",
            "company_id",
            "year",
            "details",
        ],
    )

    report.to_csv(
        FAILURE_FILE,
        index=False
    )

    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    if report.empty:
        print("[PASS] No DQ violations found.")
    else:
        print(
            report.groupby(["rule", "severity"])
            .size()
            .to_string()
        )

        critical = len(
            report[report["severity"] == "CRITICAL"]
        )

        warnings = len(
            report[report["severity"] == "WARNING"]
        )

        info = len(
            report[report["severity"] == "INFO"]
        )

        print()
        print(f"CRITICAL : {critical}")
        print(f"WARNING  : {warnings}")
        print(f"INFO     : {info}")

    print(f"\n[OK] Report created: {FAILURE_FILE}")


if __name__ == "__main__":
    main()