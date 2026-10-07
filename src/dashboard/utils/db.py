import sqlite3
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[3]
DB_PATH = ROOT_DIR / "db" / "nifty100.db"

def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Please run etl_pipeline.py first.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def run_query(query: str, params=()) -> pd.DataFrame:
    conn = get_connection()
    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        conn.close()

def get_all_companies():
    return run_query("""
        SELECT c.*, s.broad_sector, s.sub_sector, s.market_cap_category 
        FROM companies c 
        LEFT JOIN sectors s ON c.id = s.company_id
        ORDER BY c.company_name
    """)

def get_company_details(ticker: str):
    df = run_query("""
        SELECT c.*, s.broad_sector, s.sub_sector, s.market_cap_category, s.index_weight_pct
        FROM companies c 
        LEFT JOIN sectors s ON c.id = s.company_id
        WHERE c.id = ?
    """, (ticker,))
    return df.iloc[0].to_dict() if not df.empty else None

def get_company_pl(ticker: str):
    return run_query("SELECT * FROM profitandloss WHERE company_id = ? ORDER BY year ASC", (ticker,))

def get_company_bs(ticker: str):
    return run_query("SELECT * FROM balancesheet WHERE company_id = ? ORDER BY year ASC", (ticker,))

def get_company_cashflow(ticker: str):
    return run_query("SELECT * FROM cashflow WHERE company_id = ? ORDER BY year ASC", (ticker,))

def get_company_ratios(ticker: str):
    return run_query("SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year ASC", (ticker,))

def get_company_documents(ticker: str):
    return run_query("SELECT * FROM documents WHERE company_id = ? ORDER BY year DESC", (ticker,))

def get_company_prosandcons(ticker: str):
    return run_query("SELECT * FROM prosandcons WHERE company_id = ?", (ticker,))

def get_peer_groups():
    return run_query("SELECT DISTINCT peer_group_name FROM peer_groups ORDER BY peer_group_name")

def get_peer_members(group_name: str):
    return run_query("""
        SELECT pg.*, c.company_name, s.broad_sector 
        FROM peer_groups pg
        JOIN companies c ON pg.company_id = c.id
        LEFT JOIN sectors s ON c.id = s.company_id
        WHERE pg.peer_group_name = ?
    """, (group_name,))

def get_sector_summary():
    return run_query("""
        SELECT s.broad_sector, 
               COUNT(c.id) as company_count,
               AVG(c.roe_percentage) as avg_roe,
               AVG(c.roce_percentage) as avg_roce
        FROM sectors s
        JOIN companies c ON s.company_id = c.id
        GROUP BY s.broad_sector
        ORDER BY company_count DESC
    """)
