import re
import sqlite3
from pathlib import Path

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = ROOT / "data" / "raw"
DB_DIR = ROOT / "db"
OUTPUT_DIR = ROOT / "output"

DB_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

DB_PATH = DB_DIR / "nifty100.db"
DQ_REPORT_PATH = OUTPUT_DIR / "dq_report.csv"
LOAD_AUDIT_PATH = OUTPUT_DIR / "load_audit.csv"

# Raw row counts are captured before any cleaning/rejection.
RAW_ROW_COUNTS = {}


# ============================================================
# SOURCE FILES
# ============================================================

FILES = {
    "analysis": "analysis.xlsx",
    "balancesheet": "balancesheet.xlsx",
    "cashflow": "cashflow.xlsx",
    "companies": "companies.xlsx",
    "documents": "documents.xlsx",
    "profitandloss": "profitandloss.xlsx",
    "prosandcons": "prosandcons.xlsx",
    "financial_ratios": "financial_ratios.xlsx",
    "market_cap": "market_cap.xlsx",
    "peer_groups": "peer_groups.xlsx",
    "sectors": "sectors.xlsx",
    "stock_prices": "stock_prices.xlsx",
}


# ============================================================
# FIND FILE
# ============================================================

def find_file(pattern):

    matches = list(RAW_DIR.glob(f"*{pattern}"))

    if not matches:
        raise FileNotFoundError(
            f"Could not find file matching: {pattern}"
        )

    return matches[0]


# ============================================================
# COLUMN CLEANING
# ============================================================

def clean_columns(df):

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )

    return df


# ============================================================
# TICKER / COMPANY ID NORMALISATION
# ============================================================

def normalize_ticker(value):

    if pd.isna(value):
        return None

    value = str(value).strip().upper()

    return value if value else None


# ============================================================
# YEAR NORMALISATION
# ============================================================

def normalize_year(value):
    """
    Convert financial year labels into YYYY-MM format.

    Examples:
        Mar 2024      -> 2024-03
        Mar-24        -> 2024-03
        Mar 2023 15   -> 2023-03
        Mar 2016 9m   -> 2016-03

    TTM is deliberately NOT converted into a fake year.
    TTM records are handled separately during loading because
    the Sprint DQ-07 rule requires YYYY-MM.
    """

    if value is None or pd.isna(value):
        return None

    text = str(value).strip()

    if not text:
        return None

    # TTM is not an annual YYYY-MM value.
    if text.upper() == "TTM":
        return "TTM"

    # Already normalized.
    if re.fullmatch(r"\d{4}-\d{2}", text):
        return text

    # Standard 4-digit year (e.g. 2019 -> 2019-03)
    if re.fullmatch(r"\d{4}", text):
        return f"{text}-03"

    # Match values such as:
    # Mar 2024
    # Mar-24
    # Mar 2023 15
    # Mar 2016 9m
    match = re.search(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"[-\s]+"
        r"(\d{2,4})",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    month_name = match.group(1).title()
    year = int(match.group(2))

    if year < 100:
        year += 2000

    month_number = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }[month_name]

    return f"{year:04d}-{month_number:02d}"


# ============================================================
# LOAD EXCEL
# ============================================================

def load_excel(file_pattern, header=0):

    path = find_file(file_pattern)

    df = pd.read_excel(
        path,
        header=header
    )

    df = clean_columns(df)

    return df


# ============================================================
# LOAD ALL DATASETS
# ============================================================

def load_all_files():

    print("\n=== LOADING FILES ===")

    # Core files have metadata in first row.
    companies = load_excel(
        FILES["companies"],
        header=1
    )

    profitandloss = load_excel(
        FILES["profitandloss"],
        header=1
    )

    balancesheet = load_excel(
        FILES["balancesheet"],
        header=1
    )

    cashflow = load_excel(
        FILES["cashflow"],
        header=1
    )

    # Supplementary files.
    analysis = load_excel(
        FILES["analysis"],
        header=1
    )

    documents = load_excel(
        FILES["documents"],
        header=1
    )

    prosandcons = load_excel(
        FILES["prosandcons"],
        header=1
    )

    sectors = load_excel(
        FILES["sectors"],
        header=0
    )

    market_cap = load_excel(
        FILES["market_cap"],
        header=0
    )

    stock_prices = load_excel(
        FILES["stock_prices"],
        header=0
    )

    financial_ratios = load_excel(
        FILES["financial_ratios"],
        header=0
    )

    peer_groups = load_excel(
        FILES["peer_groups"],
        header=0
    )

    datasets = {
        "companies": companies,
        "profitandloss": profitandloss,
        "balancesheet": balancesheet,
        "cashflow": cashflow,
        "analysis": analysis,
        "documents": documents,
        "prosandcons": prosandcons,
        "sectors": sectors,
        "market_cap": market_cap,
        "stock_prices": stock_prices,
        "financial_ratios": financial_ratios,
        "peer_groups": peer_groups,
    }

    for name, df in datasets.items():

        RAW_ROW_COUNTS[name] = len(df)

        print(
            f"[OK] {name}: "
            f"{len(df)} rows, "
            f"{len(df.columns)} columns"
        )

    return datasets


# ============================================================
# NORMALISE DATASETS
# ============================================================

def normalize_datasets(datasets):

    print("\n=== NORMALISING DATA ===")

    # --------------------------------------------------------
    # COMPANY IDS
    # --------------------------------------------------------

    for name, df in datasets.items():

        if "company_id" in df.columns:

            df["company_id"] = (
                df["company_id"]
                .apply(normalize_ticker)
            )

    # Companies table normally uses id instead of company_id.
    if "id" in datasets["companies"].columns:

        datasets["companies"]["id"] = (
            datasets["companies"]["id"]
            .apply(normalize_ticker)
        )

    # --------------------------------------------------------
    # YEAR NORMALISATION
    # --------------------------------------------------------

    year_tables = [
        "profitandloss",
        "balancesheet",
        "cashflow",
        "documents",
        "market_cap",
        "financial_ratios",
    ]

    for table in year_tables:

        df = datasets[table]

        if "year" in df.columns:

            df["year"] = (
                df["year"]
                .apply(normalize_year)
            )
    
    # --------------------------------------------------------
    # ANALYSIS COLUMN NORMALISATION
    # --------------------------------------------------------

    analysis = datasets["analysis"].copy()

    # Convert ID columns to numeric
    if "id" in analysis.columns:
        analysis["id"] = pd.to_numeric(
            analysis["id"], errors="coerce"
        )

    if "company_id" in analysis.columns:
        analysis["company_id"] = (
            analysis["company_id"]
            .astype(str)
            .str.strip()
        )

    datasets["analysis"] = analysis.reset_index(drop=True)

    print(
        f"[OK] analysis columns corrected: "
        f"{len(analysis)} rows"
    )

    # --------------------------------------------------------
    # DOCUMENTS COLUMN NORMALISATION
    # --------------------------------------------------------

    documents = datasets["documents"].copy()

    # Convert ID columns
    if "id" in documents.columns:
        documents["id"] = pd.to_numeric(
            documents["id"], errors="coerce"
        )

    if "company_id" in documents.columns:
        documents["company_id"] = (
            documents["company_id"]
            .astype(str)
            .str.strip()
        )

    # Normalize year
    if "year" in documents.columns:
        documents["year"] = documents["year"].apply(
            normalize_year
        )

    datasets["documents"] = documents.reset_index(drop=True)

    print(
        f"[OK] documents columns corrected: "
        f"{len(documents)} rows"
    )

    # --------------------------------------------------------
    # REMOVE TTM FROM ANNUAL P&L
    # --------------------------------------------------------

    pl = datasets["profitandloss"]

    if "year" in pl.columns:

        ttm_count = (
            pl["year"]
            .astype(str)
            .str.upper()
            .eq("TTM")
            .sum()
        )

        if ttm_count > 0:

            print(
                f"[INFO] profitandloss: "
                f"removing {ttm_count} TTM rows "
                f"from annual dataset"
            )

            datasets["profitandloss"] = pl[
                ~pl["year"]
                .astype(str)
                .str.upper()
                .eq("TTM")
            ].copy()

    return datasets


# ============================================================
# DQ REPORT STORAGE
# ============================================================

dq_results = []


def add_dq(
    table,
    rule,
    severity,
    message,
    count=0
):

    dq_results.append(
        {
            "table": table,
            "rule": rule,
            "severity": severity,
            "message": message,
            "count": count,
        }
    )


# ============================================================
# DQ-01 COMPANY PRIMARY KEY
# ============================================================

def dq01(companies):

    if "id" not in companies.columns:

        add_dq(
            "companies",
            "DQ-01",
            "CRITICAL",
            "Company ID column missing",
            1,
        )

        return

    duplicates = companies[
        companies["id"].duplicated(keep=False)
    ]

    if len(duplicates) == 0:

        print("[PASS] DQ-01 Company PK uniqueness")

        add_dq(
            "companies",
            "DQ-01",
            "PASS",
            "Company primary key is unique",
            0,
        )

    else:

        print(
            f"[CRITICAL] DQ-01: "
            f"{len(duplicates)} duplicate rows"
        )

        add_dq(
            "companies",
            "DQ-01",
            "CRITICAL",
            "Duplicate company IDs",
            len(duplicates),
        )


# ============================================================
# DQ-02 ANNUAL PRIMARY KEY
# ============================================================

def dq02(datasets):

    for table in [
        "profitandloss",
        "balancesheet",
        "cashflow",
    ]:

        df = datasets[table]

        if not all(
            col in df.columns
            for col in ["company_id", "year"]
        ):
            continue

        duplicates = df.duplicated(
            subset=["company_id", "year"],
            keep=False,
        )

        count = int(duplicates.sum())

        if count == 0:

            print(
                f"[PASS] DQ-02 {table} uniqueness"
            )

            add_dq(
                table,
                "DQ-02",
                "PASS",
                "Company/year key is unique",
                0,
            )

        else:

            print(
                f"[WARNING] DQ-02 {table}: "
                f"{count} duplicate rows"
            )

            add_dq(
                table,
                "DQ-02",
                "WARNING",
                "Duplicate company/year rows",
                count,
            )


# ============================================================
# DQ-03 FOREIGN KEY
# ============================================================

def dq03(datasets):

    companies = datasets["companies"]

    valid_ids = set(
        companies["id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
    )

    child_tables = [
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

    for table in child_tables:

        df = datasets[table]

        if "company_id" not in df.columns:
            continue

        values = (
            df["company_id"]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
        )

        orphan_count = int(
            (~values.isin(valid_ids)).sum()
        )

        if orphan_count == 0:

            print(
                f"[PASS] DQ-03 {table} foreign keys"
            )

            add_dq(
                table,
                "DQ-03",
                "PASS",
                "All company IDs exist",
                0,
            )

        else:

            print(
                f"[WARNING] DQ-03 {table}: "
                f"{orphan_count} orphan rows"
            )

            add_dq(
                table,
                "DQ-03",
                "WARNING",
                "Orphan company IDs",
                orphan_count,
            )


# ============================================================
# DQ-04 BALANCE SHEET
# ============================================================

def dq04(bs):

    if not all(
        col in bs.columns
        for col in [
            "total_assets",
            "total_liabilities",
        ]
    ):
        return

    assets = pd.to_numeric(
        bs["total_assets"],
        errors="coerce",
    )

    liabilities = pd.to_numeric(
        bs["total_liabilities"],
        errors="coerce",
    )

    valid = assets.notna() & liabilities.notna()

    difference = (
        (assets - liabilities).abs()
        / assets.abs().replace(0, pd.NA)
    )

    violations = int(
        (valid & (difference >= 0.01)).sum()
    )

    print(
        f"[INFO] DQ-04 Balance Sheet: "
        f"{violations} violations"
    )

    add_dq(
        "balancesheet",
        "DQ-04",
        "WARNING",
        "Assets/liabilities differ by 1% or more",
        violations,
    )


# ============================================================
# DQ-05 OPM
# ============================================================

def dq05(pl):

    required = [
        "sales",
        "operating_profit",
        "opm_percentage",
    ]

    if not all(
        col in pl.columns
        for col in required
    ):
        return

    sales = pd.to_numeric(
        pl["sales"],
        errors="coerce",
    )

    operating_profit = pd.to_numeric(
        pl["operating_profit"],
        errors="coerce",
    )

    source_opm = pd.to_numeric(
        pl["opm_percentage"],
        errors="coerce",
    )

    calculated_opm = (
        operating_profit / sales
    ) * 100

    valid = (
        sales.notna()
        & operating_profit.notna()
        & source_opm.notna()
        & (sales != 0)
    )

    violations = int(
        (
            valid
            & (
                (source_opm - calculated_opm).abs()
                >= 1
            )
        ).sum()
    )

    print(
        f"[INFO] DQ-05 OPM cross-check: "
        f"{violations} violations"
    )

    add_dq(
        "profitandloss",
        "DQ-05",
        "WARNING",
        "OPM differs from calculated value by >=1%",
        violations,
    )


# ============================================================
# DQ-06 POSITIVE SALES
# ============================================================

def dq06(pl):

    if "sales" not in pl.columns:
        return

    sales = pd.to_numeric(
        pl["sales"],
        errors="coerce",
    )

    violations = int(
        (
            sales.notna()
            & (sales <= 0)
        ).sum()
    )

    print(
        f"[INFO] DQ-06 Positive sales: "
        f"{violations} violations"
    )

    add_dq(
        "profitandloss",
        "DQ-06",
        "WARNING",
        "Non-positive sales",
        violations,
    )


# ============================================================
# DQ-07 YEAR FORMAT
# ============================================================

def dq07(datasets):

    pattern = r"^\d{4}-\d{2}$"

    for table in [
        "profitandloss",
        "balancesheet",
        "cashflow",
        "financial_ratios",
    ]:

        df = datasets[table]

        if "year" not in df.columns:
            continue

        invalid = (
            ~df["year"]
            .astype(str)
            .str.match(pattern, na=False)
        )

        count = int(invalid.sum())

        if count == 0:

            print(
                f"[PASS] DQ-07 {table} year format"
            )

            add_dq(
                table,
                "DQ-07",
                "PASS",
                "All year values match YYYY-MM",
                0,
            )

        else:

            print(
                f"[CRITICAL] DQ-07 {table}: "
                f"{count} invalid year values"
            )

            add_dq(
                table,
                "DQ-07",
                "CRITICAL",
                "Invalid YYYY-MM year values",
                count,
            )


# ============================================================
# DQ-08 TICKER FORMAT
# ============================================================

def dq08(companies):

    if "id" not in companies.columns:
        return

    tickers = (
        companies["id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    invalid = (
        (tickers.str.len() < 2)
        | (tickers.str.len() > 12)
    )

    count = int(invalid.sum())

    if count == 0:

        print("[PASS] DQ-08 Ticker format")

        add_dq(
            "companies",
            "DQ-08",
            "PASS",
            "All tickers have valid length",
            0,
        )

    else:

        print(
            f"[CRITICAL] DQ-08: "
            f"{count} invalid tickers"
        )

        add_dq(
            "companies",
            "DQ-08",
            "CRITICAL",
            "Ticker length outside 2-12",
            count,
        )


# ============================================================
# DQ-09 NET CASH
# ============================================================

def dq09(cf):

    required = [
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]

    if not all(
        col in cf.columns
        for col in required
    ):
        return

    cfo = pd.to_numeric(
        cf["operating_activity"],
        errors="coerce",
    )

    cfi = pd.to_numeric(
        cf["investing_activity"],
        errors="coerce",
    )

    cff = pd.to_numeric(
        cf["financing_activity"],
        errors="coerce",
    )

    net = pd.to_numeric(
        cf["net_cash_flow"],
        errors="coerce",
    )

    calculated = cfo + cfi + cff

    valid = (
        cfo.notna()
        & cfi.notna()
        & cff.notna()
        & net.notna()
    )

    violations = int(
        (
            valid
            & ((net - calculated).abs() > 10)
        ).sum()
    )

    print(
        f"[INFO] DQ-09 Net cash flow: "
        f"{violations} violations"
    )

    add_dq(
        "cashflow",
        "DQ-09",
        "WARNING",
        "Net cash flow differs by more than 10 Cr",
        violations,
    )


# ============================================================
# DQ-10 FIXED ASSETS
# ============================================================

def dq10(bs):

    if "fixed_assets" not in bs.columns:
        return

    fixed_assets = pd.to_numeric(
        bs["fixed_assets"],
        errors="coerce",
    )

    violations = int(
        (
            fixed_assets.notna()
            & (fixed_assets < 0)
        ).sum()
    )

    print(
        f"[INFO] DQ-10 Fixed assets: "
        f"{violations} violations"
    )

    add_dq(
        "balancesheet",
        "DQ-10",
        "WARNING",
        "Negative fixed assets",
        violations,
    )


# ============================================================
# DQ-11 TAX RATE
# ============================================================

def dq11(pl):

    if "tax_percentage" not in pl.columns:
        return

    tax = pd.to_numeric(
        pl["tax_percentage"],
        errors="coerce",
    )

    violations = int(
        (
            tax.notna()
            & (
                (tax < 0)
                | (tax > 60)
            )
        ).sum()
    )

    print(
        f"[INFO] DQ-11 Tax rate: "
        f"{violations} violations"
    )

    add_dq(
        "profitandloss",
        "DQ-11",
        "WARNING",
        "Tax rate outside 0-60%",
        violations,
    )


# ============================================================
# DQ-12 DIVIDEND PAYOUT
# ============================================================

def dq12(pl):

    if "dividend_payout" not in pl.columns:
        return

    payout = pd.to_numeric(
        pl["dividend_payout"],
        errors="coerce",
    )

    violations = int(
        (
            payout.notna()
            & (
                (payout < 0)
                | (payout > 200)
            )
        ).sum()
    )

    print(
        f"[INFO] DQ-12 Dividend payout: "
        f"{violations} violations"
    )

    add_dq(
        "profitandloss",
        "DQ-12",
        "WARNING",
        "Dividend payout outside 0-200%",
        violations,
    )


# ============================================================
# DQ-13 URL VALIDITY
# ============================================================

def dq13(documents):

    url_column = None

    for candidate in [
        "annual_report",
        "annual_report_url",
        "url",
    ]:

        if candidate in documents.columns:
            url_column = candidate
            break

    if url_column is None:

        add_dq(
            "documents",
            "DQ-13",
            "WARNING",
            "Annual report URL column not found",
            0,
        )

        return

    violations = 0
    url_pattern = re.compile(r"^https?://[^\s]+", re.IGNORECASE)

    for url in documents[url_column].dropna():

        url_str = str(url).strip()
        if not url_str or not url_pattern.match(url_str):
            violations += 1

    print(
        f"[INFO] DQ-13 URL validation: "
        f"{violations} violations"
    )

    add_dq(
        "documents",
        "DQ-13",
        "WARNING",
        "Invalid annual report URLs",
        violations,
    )


# ============================================================
# DQ-14 EPS SIGN
# ============================================================

def dq14(pl):

    required = [
        "net_profit",
        "eps",
    ]

    if not all(
        col in pl.columns
        for col in required
    ):
        return

    net_profit = pd.to_numeric(
        pl["net_profit"],
        errors="coerce",
    )

    eps = pd.to_numeric(
        pl["eps"],
        errors="coerce",
    )

    violations = int(
        (
            net_profit.notna()
            & eps.notna()
            & (net_profit > 0)
            & (eps <= 0)
        ).sum()
    )

    print(
        f"[INFO] DQ-14 EPS sign: "
        f"{violations} violations"
    )

    add_dq(
        "profitandloss",
        "DQ-14",
        "WARNING",
        "Positive net profit with non-positive EPS",
        violations,
    )


# ============================================================
# DQ-15 STRICT BALANCE
# ============================================================

def dq15(bs):

    required = [
        "total_assets",
        "total_liabilities",
    ]

    if not all(
        col in bs.columns
        for col in required
    ):
        return

    assets = pd.to_numeric(
        bs["total_assets"],
        errors="coerce",
    )

    liabilities = pd.to_numeric(
        bs["total_liabilities"],
        errors="coerce",
    )

    violations = int(
        (
            assets.notna()
            & liabilities.notna()
            & (assets != liabilities)
        ).sum()
    )

    print(
        f"[INFO] DQ-15 Strict balance: "
        f"{violations} differences"
    )

    add_dq(
        "balancesheet",
        "DQ-15",
        "INFO",
        "Assets and liabilities differ exactly",
        violations,
    )


# ============================================================
# DQ-16 COVERAGE
# ============================================================

def dq16(datasets):

    for table in [
        "profitandloss",
        "balancesheet",
        "cashflow",
    ]:

        df = datasets[table]

        if not all(
            col in df.columns
            for col in ["company_id", "year"]
        ):
            continue

        coverage = (
            df.groupby("company_id")["year"]
            .nunique()
        )

        violations = int(
            (coverage < 5).sum()
        )

        print(
            f"[INFO] DQ-16 {table} coverage: "
            f"{violations} companies below 5 years"
        )

        add_dq(
            table,
            "DQ-16",
            "WARNING",
            "Companies with fewer than 5 years",
            violations,
        )


# ============================================================
# BASIC DATA CLEANING
# ============================================================

def clean_data(datasets):

    print("\n=== BASIC DATA QUALITY CHECKS ===")

    companies = datasets["companies"]

    # --------------------------------------------------------
    # DQ-01
    # --------------------------------------------------------

    dq01(companies)

    # --------------------------------------------------------
    # DQ-02
    # --------------------------------------------------------

    dq02(datasets)

    # --------------------------------------------------------
    # Remove annual duplicates
    # --------------------------------------------------------

    for table in [
        "profitandloss",
        "balancesheet",
        "cashflow",
    ]:

        df = datasets[table]

        if all(
            col in df.columns
            for col in ["company_id", "year"]
        ):

            before = len(df)

            df = df.drop_duplicates(
                subset=["company_id", "year"],
                keep="last",
            )

            removed = before - len(df)

            if removed > 0:

                print(
                    f"[WARNING] {table}: "
                    f"removed {removed} duplicate rows"
                )

            datasets[table] = df

    # --------------------------------------------------------
    # DQ-03
    # --------------------------------------------------------

    dq03(datasets)

    valid_ids = set(
        companies["id"]
        .dropna()
        .astype(str)
        .str.upper()
        .str.strip()
    )

    child_tables = [
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

    for table in child_tables:

        df = datasets[table]

        if "company_id" not in df.columns:
            continue

        mask = (
            df["company_id"]
            .astype(str)
            .str.upper()
            .str.strip()
            .isin(valid_ids)
        )

        removed = int((~mask).sum())

        if removed > 0:

            print(
                f"[WARNING] {table}: "
                f"{removed} orphan rows removed"
            )

            datasets[table] = df[mask].copy()

    # --------------------------------------------------------
    # DQ-07
    # --------------------------------------------------------

    dq07(datasets)

    # --------------------------------------------------------
    # DQ-08
    # --------------------------------------------------------

    dq08(companies)

    # --------------------------------------------------------
    # DQ-04
    # --------------------------------------------------------

    dq04(datasets["balancesheet"])

    # --------------------------------------------------------
    # DQ-05
    # --------------------------------------------------------

    dq05(datasets["profitandloss"])

    # --------------------------------------------------------
    # DQ-06
    # --------------------------------------------------------

    dq06(datasets["profitandloss"])

    # --------------------------------------------------------
    # DQ-09
    # --------------------------------------------------------

    dq09(datasets["cashflow"])

    # --------------------------------------------------------
    # DQ-10
    # --------------------------------------------------------

    dq10(datasets["balancesheet"])

    # --------------------------------------------------------
    # DQ-11
    # --------------------------------------------------------

    dq11(datasets["profitandloss"])

    # --------------------------------------------------------
    # DQ-12
    # --------------------------------------------------------

    dq12(datasets["profitandloss"])

    # --------------------------------------------------------
    # DQ-13
    # --------------------------------------------------------

    dq13(datasets["documents"])

    # --------------------------------------------------------
    # DQ-14
    # --------------------------------------------------------

    dq14(datasets["profitandloss"])

    # --------------------------------------------------------
    # DQ-15
    # --------------------------------------------------------

    dq15(datasets["balancesheet"])

    # --------------------------------------------------------
    # DQ-16
    # --------------------------------------------------------

    dq16(datasets)

    return datasets


# ============================================================
# SQLITE LOAD USING schema.sql
# ============================================================

def load_sqlite(datasets):

    print("\n=== LOADING SQLITE DATABASE ===")

    schema_path = DB_DIR / "schema.sql"

    if not schema_path.exists():

        raise FileNotFoundError(
            f"Schema file not found: {schema_path}"
        )

    # --------------------------------------------------------
    # REMOVE OLD DATABASE
    # --------------------------------------------------------

    if DB_PATH.exists():

        DB_PATH.unlink()

        print(
            "[OK] Old database removed"
        )

    # --------------------------------------------------------
    # CREATE NEW DATABASE
    # --------------------------------------------------------

    conn = sqlite3.connect(DB_PATH)

    # IMPORTANT:
    # Enable foreign key enforcement.
    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    print(
        "[OK] SQLite database connection created"
    )

    print(
        "[OK] Foreign keys enabled"
    )

    # --------------------------------------------------------
    # CREATE TABLES FROM schema.sql
    # --------------------------------------------------------

    schema_sql = schema_path.read_text(
        encoding="utf-8"
    )

    conn.executescript(
        schema_sql
    )

    print(
        "[OK] Database schema created from schema.sql"
    )

    # --------------------------------------------------------
    # TABLE LOAD ORDER
    #
    # companies must be loaded first because all other
    # tables contain foreign keys referencing companies.
    # --------------------------------------------------------

    load_order = [
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

    # --------------------------------------------------------
    # INSERT DATA
    # --------------------------------------------------------

    for table in load_order:

        if table not in datasets:

            print(
                f"[WARNING] Dataset not found: {table}"
            )

            continue

        df = datasets[table]

        # IMPORTANT:
        # append is used instead of replace.
        #
        # replace would destroy the tables created by
        # schema.sql and therefore remove the PRIMARY KEY
        # and FOREIGN KEY definitions.
        df.to_sql(
            table,
            conn,
            if_exists="append",
            index=False,
        )

        print(
            f"[OK] Data loaded: {table} "
            f"({len(df)} rows)"
        )

    # --------------------------------------------------------
    # COMMIT
    # --------------------------------------------------------

    conn.commit()

    print(
        "\n[OK] All data committed to SQLite"
    )

    # --------------------------------------------------------
    # FOREIGN KEY VALIDATION
    # --------------------------------------------------------

    print(
        "\n=== FOREIGN KEY VALIDATION ==="
    )

    fk_errors = conn.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if len(fk_errors) == 0:

        print(
            "[PASS] PRAGMA foreign_key_check -> 0 rows"
        )

    else:

        print(
            f"[CRITICAL] Foreign key violations: "
            f"{len(fk_errors)}"
        )

        print(
            "\nFirst 10 foreign key errors:"
        )

        for error in fk_errors[:10]:

            print(error)

        conn.close()

        raise RuntimeError(
            "Foreign key validation failed."
        )

    # --------------------------------------------------------
    # VERIFY TABLES
    # --------------------------------------------------------

    print(
        "\n=== SQLITE TABLE VERIFICATION ==="
    )

    tables = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    print(
        "\n[OK] SQLite tables:"
    )

    for table in tables:

        print(
            f"  - {table[0]}"
        )

    # --------------------------------------------------------
    # VERIFY ROW COUNTS
    # --------------------------------------------------------

    print(
        "\n=== SQLITE ROW COUNTS ==="
    )

    for table in load_order:

        result = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()

        row_count = result[0]

        print(
            f"  {table}: {row_count} rows"
        )

    # --------------------------------------------------------
    # VERIFY FOREIGN KEY PRAGMA
    # --------------------------------------------------------

    fk_status = conn.execute(
        "PRAGMA foreign_keys"
    ).fetchone()[0]

    if fk_status == 1:

        print(
            "\n[PASS] PRAGMA foreign_keys = ON"
        )

    else:

        print(
            "\n[CRITICAL] Foreign keys are disabled"
        )

        conn.close()

        raise RuntimeError(
            "SQLite foreign keys are not enabled."
        )

    # --------------------------------------------------------
    # VERIFY PRIMARY KEY / FOREIGN KEY STRUCTURE
    # --------------------------------------------------------

    print(
        "\n=== SQLITE CONSTRAINT VERIFICATION ==="
    )

    important_tables = [
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
    ]

    for table in important_tables:

        foreign_keys = conn.execute(
            f"PRAGMA foreign_key_list({table})"
        ).fetchall()

        if table == "companies":

            print(
                f"[PASS] {table}: PRIMARY KEY defined"
            )

        elif foreign_keys:

            print(
                f"[PASS] {table}: FOREIGN KEY defined"
            )

        else:

            print(
                f"[WARNING] {table}: "
                f"FOREIGN KEY not found"
            )

    # --------------------------------------------------------
    # CLOSE DATABASE
    # --------------------------------------------------------

    conn.close()

    print(
        "\n[OK] Database created successfully:"
    )

    print(
        DB_PATH
    )

    print(
        "\n=== SQLITE LOAD COMPLETED ==="
    )


# ============================================================
# DQ REPORT
# ============================================================

def generate_dq_report(datasets):

    print(
        "\n=== GENERATING DQ REPORT ==="
    )

    rows = []

    for table, df in datasets.items():

        rows.append(
            {
                "table": table,
                "rows": len(df),
                "columns": len(df.columns),
                "missing_values": int(
                    df.isna().sum().sum()
                ),
            }
        )

    report = pd.DataFrame(rows)

    report.to_csv(
        DQ_REPORT_PATH,
        index=False,
    )

    print(
        report.to_string(index=False)
    )

    print(
        f"\n[OK] DQ report created: "
        f"{DQ_REPORT_PATH}"
    )


# ============================================================
# LOAD AUDIT
# ============================================================

def generate_load_audit(datasets):

    """
    Create the Sprint 1 load_audit.csv deliverable.

    Raw rows are captured before cleaning. The difference between
    raw rows and final rows represents rows removed during ETL
    because of TTM filtering, duplicate removal, or orphan removal.
    """

    print(
        "\n=== GENERATING LOAD AUDIT ==="
    )

    audit_rows = []

    for table, df in datasets.items():

        raw_rows = int(
            RAW_ROW_COUNTS.get(
                table,
                len(df)
            )
        )

        loaded_rows = int(
            len(df)
        )

        rejected_rows = max(
            raw_rows - loaded_rows,
            0
        )

        if rejected_rows == 0:

            status = "LOADED"

            reason = (
                "No rows rejected"
            )

        else:

            status = (
                "LOADED_WITH_REJECTIONS"
            )

            reasons = []

            if table == "profitandloss":

                reasons.append(
                    "TTM rows, duplicate company/year rows, "
                    "and/or orphan company IDs"
                )

            if table in {
                "balancesheet",
                "cashflow"
            }:

                reasons.append(
                    "duplicate company/year rows "
                    "and/or orphan company IDs"
                )

            if table == "financial_ratios":

                reasons.append(
                    "orphan company IDs"
                )

            if not reasons:

                reasons.append(
                    "Rows removed during ETL quality cleaning"
                )

            reason = "; ".join(
                reasons
            )

        audit_rows.append(
            {
                "table": table,
                "raw_rows": raw_rows,
                "loaded_rows": loaded_rows,
                "rejected_rows": rejected_rows,
                "status": status,
                "rejection_reason": reason,
            }
        )

    audit = pd.DataFrame(
        audit_rows
    )

    audit.to_csv(
        LOAD_AUDIT_PATH,
        index=False
    )

    print(
        audit.to_string(
            index=False
        )
    )

    print(
        f"\n[OK] Load audit created: "
        f"{LOAD_AUDIT_PATH}"
    )

    return audit


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 70
    )

    print(
        "NIFTY 100 DATA INGESTION & ETL PIPELINE"
    )

    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # STEP 1: LOAD FILES
    # --------------------------------------------------------

    datasets = load_all_files()

    # --------------------------------------------------------
    # STEP 2: NORMALISE DATA
    # --------------------------------------------------------

    datasets = normalize_datasets(
        datasets
    )

    # --------------------------------------------------------
    # STEP 3: DATA QUALITY CLEANING
    # --------------------------------------------------------

    datasets = clean_data(
        datasets
    )

    # --------------------------------------------------------
    # STEP 4: CREATE SQLITE DATABASE
    # --------------------------------------------------------

    load_sqlite(
        datasets
    )

    # --------------------------------------------------------
    # STEP 5: GENERATE LOAD AUDIT
    # --------------------------------------------------------

    generate_load_audit(
        datasets
    )

    # --------------------------------------------------------
    # STEP 6: GENERATE DQ REPORT
    # --------------------------------------------------------

    generate_dq_report(
        datasets
    )

    # --------------------------------------------------------
    # FINAL MESSAGE
    # --------------------------------------------------------

    print(
        "\n" + "=" * 70
    )

    print(
        "ETL PIPELINE COMPLETED SUCCESSFULLY"
    )

    print(
        "=" * 70
    )

    print(
        f"\nDatabase: {DB_PATH}"
    )

    print(
        f"DQ Report: {DQ_REPORT_PATH}"
    )

    print(
        f"Load Audit: {LOAD_AUDIT_PATH}"
    )


    try:
        import sys
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from src.etl.validator import main as run_validation
        run_validation()
    except Exception as err:
        print(f"[WARNING] Could not run validator: {err}")


# ============================================================
# RUN PIPELINE
# ============================================================

if __name__ == "__main__":

    main()