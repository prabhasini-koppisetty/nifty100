import sqlite3
from pathlib import Path
import pandas as pd

from src.etl.normaliser import normalize_ticker, normalize_year

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
DB_DIR = ROOT / "db"
OUTPUT_DIR = ROOT / "output"

DB_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

DB_PATH = DB_DIR / "nifty100.db"
DQ_REPORT_PATH = OUTPUT_DIR / "dq_report.csv"
LOAD_AUDIT_PATH = OUTPUT_DIR / "load_audit.csv"

RAW_ROW_COUNTS = {}

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


def find_file(pattern):
    matches = list(RAW_DIR.glob(f"*{pattern}"))
    if not matches:
        raise FileNotFoundError(f"Could not find file matching: {pattern}")
    return matches[0]


def clean_columns(df):
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )
    return df


def load_excel(file_pattern, header=0):
    path = find_file(file_pattern)
    df = pd.read_excel(path, header=header)
    df = clean_columns(df)
    return df


def load_all_files():
    print("\n=== LOADING FILES ===")

    companies = load_excel(FILES["companies"], header=1)
    profitandloss = load_excel(FILES["profitandloss"], header=1)
    balancesheet = load_excel(FILES["balancesheet"], header=1)
    cashflow = load_excel(FILES["cashflow"], header=1)
    analysis = load_excel(FILES["analysis"], header=1)
    documents = load_excel(FILES["documents"], header=1)
    prosandcons = load_excel(FILES["prosandcons"], header=1)
    sectors = load_excel(FILES["sectors"], header=0)
    market_cap = load_excel(FILES["market_cap"], header=0)
    stock_prices = load_excel(FILES["stock_prices"], header=0)
    financial_ratios = load_excel(FILES["financial_ratios"], header=0)
    peer_groups = load_excel(FILES["peer_groups"], header=0)

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
        print(f"[OK] {name}: {len(df)} rows, {len(df.columns)} columns")

    return datasets


def load_sqlite(datasets):
    print("\n=== LOADING SQLITE DATABASE ===")
    schema_path = DB_DIR / "schema.sql"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    if DB_PATH.exists():
        DB_PATH.unlink()
        print("[OK] Old database removed")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    schema_sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(schema_sql)

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

    for table in load_order:
        if table not in datasets:
            continue

        df = datasets[table]
        df.to_sql(table, conn, if_exists="append", index=False)
        print(f"[OK] Data loaded: {table} ({len(df)} rows)")

    conn.commit()

    fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    if len(fk_errors) != 0:
        conn.close()
        raise RuntimeError(f"Foreign key validation failed with {len(fk_errors)} errors.")

    conn.close()
    return DB_PATH
