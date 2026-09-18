import pandas as pd
import sqlite3
import glob
import os
import re

# ==============================
# PROJECT PATHS
# ==============================

RAW = "data/raw"
DB = "db/nifty100.db"
OUTPUT = "output"

os.makedirs("db", exist_ok=True)
os.makedirs(OUTPUT, exist_ok=True)


# ==============================
# INPUT FILES
# ==============================

files = {
    "companies": "*companies.xlsx",
    "profitandloss": "*profitandloss.xlsx",
    "balancesheet": "*balancesheet.xlsx",
    "cashflow": "*cashflow.xlsx",
    "analysis": "*analysis.xlsx",
    "documents": "*documents.xlsx",
    "prosandcons": "*prosandcons.xlsx",
    "sectors": "*sectors.xlsx",
    "market_cap": "*market_cap.xlsx",
    "stock_prices": "*stock_prices.xlsx",
    "financial_ratios": "*financial_ratios.xlsx",
    "peer_groups": "*peer_groups.xlsx",
}


# Core files have a metadata row before the real headers
core = {
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "documents",
    "prosandcons",
}


# ==============================
# YEAR NORMALIZATION
# ==============================

def normalize_year(x):

    if pd.isna(x):
        return None

    x = str(x).strip()

    # TTM = trailing twelve months
    if x.upper() == "TTM":
        return "TTM"

    # Handles:
    # Mar 2024
    # Mar 2016 9m
    # Mar 2023 15
    match = re.search(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})",
        x,
        re.IGNORECASE
    )

    if match:

        month = pd.to_datetime(
            match.group(1),
            format="%b"
        ).month

        year = match.group(2)

        return f"{year}-{month:02d}"

    return x


# ==============================
# LOAD DATA
# ==============================

data = {}

print("\n=== LOADING FILES ===")

for table, pattern in files.items():

    matches = glob.glob(
        os.path.join(RAW, pattern)
    )

    if not matches:
        print(f"[ERROR] Missing: {table}")
        continue

    path = matches[0]

    # Core files -> header row 1
    # Supplementary files -> header row 0
    if table in core:
        df = pd.read_excel(
            path,
            header=1
        )
    else:
        df = pd.read_excel(
            path,
            header=0
        )

    # ==============================
    # CLEAN COLUMN NAMES
    # ==============================

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(
            r"[^\w]+",
            "_",
            regex=True
        )
        .str.strip("_")
    )

    # Remove completely empty rows
    df = df.dropna(
        how="all"
    )

    # ==============================
    # NORMALIZE COMPANY ID
    # ==============================

    if "company_id" in df.columns:

        df["company_id"] = (
            df["company_id"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

    # Normalize company primary ID
    if table == "companies" and "id" in df.columns:

        df["id"] = (
            df["id"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

    # ==============================
    # NORMALIZE YEAR
    # ==============================

    if "year" in df.columns:

        df["year"] = df["year"].apply(
            normalize_year
        )

    # Store dataframe
    data[table] = df

    print(
        f"[OK] {table}: "
        f"{len(df)} rows, "
        f"{len(df.columns)} columns"
    )


# ==============================
# DATA QUALITY CHECKS
# ==============================

print("\n=== BASIC DATA QUALITY CHECKS ===")

issues = []


# ==============================
# DQ-01 COMPANY PK UNIQUENESS
# ==============================

if "companies" in data:

    companies = data["companies"]

    if "id" in companies.columns:

        duplicates = companies[
            "id"
        ].duplicated().sum()

        if duplicates:

            issues.append(
                f"DQ-01: {duplicates} duplicate company IDs"
            )

            print(
                f"[CRITICAL] DQ-01: "
                f"{duplicates} duplicate company IDs"
            )

        else:

            print(
                "[PASS] DQ-01 Company PK uniqueness"
            )


# ==============================
# DQ-02 ANNUAL PK UNIQUENESS
# ==============================

for table in [
    "profitandloss",
    "balancesheet",
    "cashflow"
]:

    if table not in data:
        continue

    df = data[table]

    if {
        "company_id",
        "year"
    }.issubset(df.columns):

        duplicates = df.duplicated(
            subset=[
                "company_id",
                "year"
            ]
        ).sum()

        if duplicates:

            print(
                f"[WARNING] DQ-02 {table}: "
                f"{duplicates} duplicate rows "
                f"- keeping last"
            )

            data[table] = df.drop_duplicates(
                subset=[
                    "company_id",
                    "year"
                ],
                keep="last"
            )

        else:

            print(
                f"[PASS] DQ-02 {table} "
                f"annual uniqueness"
            )


# ==============================
# DQ-03 FOREIGN KEY INTEGRITY
# ==============================

if "companies" in data:

    valid_ids = set(
        data["companies"]["id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    for table, df in list(data.items()):

        if (
            table != "companies"
            and "company_id" in df.columns
        ):

            orphan_mask = (
                ~df["company_id"].isin(valid_ids)
            )

            orphan_count = orphan_mask.sum()

            if orphan_count:

                print(
                    f"[WARNING] DQ-03 {table}: "
                    f"{orphan_count} orphan rows removed"
                )

                data[table] = df.loc[
                    ~orphan_mask
                ].copy()

            else:

                print(
                    f"[PASS] DQ-03 {table} "
                    f"foreign keys"
                )


# ==============================
# DQ-07 YEAR FORMAT
# ==============================

for table, df in data.items():

    if "year" not in df.columns:
        continue

    # TTM is allowed as a special period
    valid_date = df["year"].astype(str).str.match(
        r"^\d{4}-\d{2}$"
    )

    valid_ttm = (
        df["year"].astype(str).str.upper()
        == "TTM"
    )

    bad = ~(valid_date | valid_ttm)

    if bad.sum():

        print(
            f"[WARNING] DQ-07 {table}: "
            f"{bad.sum()} invalid year values"
        )

    else:

        print(
            f"[PASS] DQ-07 {table} "
            f"year format"
        )


# ==============================
# DQ-08 TICKER FORMAT
# ==============================

if (
    "companies" in data
    and "id" in data["companies"].columns
):

    companies = data["companies"]

    bad = ~companies["id"].astype(str).str.match(
        r"^[A-Z0-9&.-]{2,12}$"
    )

    if bad.sum():

        print(
            f"[WARNING] DQ-08 "
            f"{bad.sum()} invalid company IDs"
        )

    else:

        print(
            "[PASS] DQ-08 Ticker format"
        )


# ==============================
# DQ-04 BALANCE SHEET CHECK
# ==============================

if "balancesheet" in data:

    df = data["balancesheet"]

    # Try to locate columns automatically
    asset_col = next(
        (
            c for c in df.columns
            if "total_assets" in c
        ),
        None
    )

    liability_col = next(
        (
            c for c in df.columns
            if "total_liabilities" in c
        ),
        None
    )

    if asset_col and liability_col:

        assets = pd.to_numeric(
            df[asset_col],
            errors="coerce"
        )

        liabilities = pd.to_numeric(
            df[liability_col],
            errors="coerce"
        )

        valid = assets > 0

        difference = (
            (assets - liabilities).abs()
            / assets
        )

        violations = (
            difference[valid] >= 0.01
        ).sum()

        print(
            f"[INFO] DQ-04 Balance Sheet: "
            f"{violations} rows outside 1% tolerance"
        )


# ==============================
# DQ-06 POSITIVE SALES
# ==============================

if "profitandloss" in data:

    df = data["profitandloss"]

    sales_col = next(
        (
            c for c in df.columns
            if c == "sales"
        ),
        None
    )

    if sales_col:

        sales = pd.to_numeric(
            df[sales_col],
            errors="coerce"
        )

        negative_sales = (
            sales <= 0
        ).sum()

        print(
            f"[INFO] DQ-06 Positive Sales: "
            f"{negative_sales} non-positive values"
        )


# ==============================
# LOAD SQLITE
# ==============================

print("\n=== LOADING SQLITE DATABASE ===")

conn = sqlite3.connect(DB)

for table, df in data.items():

    df.to_sql(
        table,
        conn,
        if_exists="replace",
        index=False
    )

    print(
        f"[OK] SQLite table created: {table}"
    )

conn.close()


# ==============================
# DQ REPORT
# ==============================

print("\n=== GENERATING DQ REPORT ===")

report = []

for table, df in data.items():

    report.append({
        "table": table,
        "rows": len(df),
        "columns": len(df.columns),
        "missing_values": int(
            df.isna().sum().sum()
        )
    })

report_df = pd.DataFrame(report)

report_df.to_csv(
    os.path.join(
        OUTPUT,
        "dq_report.csv"
    ),
    index=False
)

print(
    report_df.to_string(
        index=False
    )
)


# ==============================
# FINAL MESSAGE
# ==============================

print("\n===================================")
print("ETL PIPELINE COMPLETED SUCCESSFULLY")
print(f"Database: {DB}")
print(f"DQ Report: {OUTPUT}/dq_report.csv")
print("===================================")