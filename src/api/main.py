from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

DB_PATH = ROOT_DIR / "db" / "nifty100.db"

from src.screener.engine import (
    load_screener_config,
    load_financial_data,
    run_preset,
    run_custom_screener
)

app = FastAPI(
    title="Nifty 100 Financial Intelligence API",
    description="RESTful API providing fundamental financial analytics, KPIs, stock screener presets, and peer percentile rankings.",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    if not DB_PATH.exists():
        raise HTTPException(status_code=500, detail="Database file nifty100.db not found.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "online",
        "service": "Nifty 100 Financial Intelligence REST API",
        "documentation": "/docs",
        "version": "3.0.0"
    }


@app.get("/api/v1/health", tags=["Health"])
def health_check():
    conn = get_db()
    cursor = conn.cursor()
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
    table_counts = {}
    for t in tables:
        tname = t['name']
        cnt = cursor.execute(f"SELECT COUNT(*) FROM {tname}").fetchone()[0]
        table_counts[tname] = cnt
    conn.close()
    return {
        "status": "healthy",
        "database": str(DB_PATH.name),
        "tables": table_counts
    }


@app.get("/api/v1/companies", tags=["Companies"])
def list_companies(sector: Optional[str] = Query(None, description="Filter by broad sector")):
    conn = get_db()
    cursor = conn.cursor()
    query = """
        SELECT c.*, s.broad_sector, s.sub_sector, s.market_cap_category
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
    """
    params = []
    if sector:
        query += " WHERE s.broad_sector = ?"
        params.append(sector)
    query += " ORDER BY c.id ASC"
    
    rows = cursor.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/v1/companies/{ticker}", tags=["Companies"])
def get_company(ticker: str):
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute("""
        SELECT c.*, s.broad_sector, s.sub_sector, s.market_cap_category
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        WHERE c.id = ?
    """, (ticker.upper(),)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found.")
    return dict(row)


@app.get("/api/v1/companies/{ticker}/pl", tags=["Financial Statements"])
def get_company_pl(ticker: str):
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM profitandloss WHERE company_id = ? ORDER BY year ASC", (ticker.upper(),)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/v1/companies/{ticker}/bs", tags=["Financial Statements"])
def get_company_bs(ticker: str):
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM balancesheet WHERE company_id = ? ORDER BY year ASC", (ticker.upper(),)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/v1/companies/{ticker}/cashflow", tags=["Financial Statements"])
def get_company_cashflow(ticker: str):
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM cashflow WHERE company_id = ? ORDER BY year ASC", (ticker.upper(),)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/v1/companies/{ticker}/ratios", tags=["Financial Ratios"])
def get_company_ratios(ticker: str):
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year ASC", (ticker.upper(),)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==========================================
# SPRINT 3 SCREENER API ENDPOINTS
# ==========================================

@app.get("/api/screener/presets", tags=["Sprint 3 Screener"])
def get_screener_presets():
    """List available preset screeners and criteria."""
    cfg = load_screener_config()
    return cfg.get("presets", {})


@app.get("/api/screener/{preset_name}", tags=["Sprint 3 Screener"])
def execute_preset_screener(preset_name: str):
    """Run a preset screener against Nifty 100 universe."""
    cfg = load_screener_config()
    presets = cfg.get("presets", {})
    if preset_name not in presets:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_name}' not found. Available: {list(presets.keys())}")
    
    df_data = load_financial_data()
    res_df = run_preset(df_data, preset_name, cfg)
    return res_df.to_dict("records")


@app.post("/api/screener/custom", tags=["Sprint 3 Screener"])
def execute_custom_screener(filters: Dict[str, Any] = Body(...)):
    """Run custom threshold screening with arbitrary filter parameters."""
    df_data = load_financial_data()
    res_df = run_custom_screener(df_data, filters)
    return res_df.to_dict("records")


@app.get("/api/v1/screener", tags=["Sprint 3 Screener"])
def run_legacy_screener(
    min_roe: Optional[float] = Query(None, description="Minimum ROE %"),
    min_roce: Optional[float] = Query(None, description="Minimum ROCE %"),
    max_de: Optional[float] = Query(None, description="Maximum Debt-to-Equity"),
    sector: Optional[str] = Query(None, description="Broad sector filter")
):
    conn = get_db()
    cursor = conn.cursor()
    query = """
        SELECT c.id, c.company_name, s.broad_sector, s.sub_sector, c.roe_percentage, c.roce_percentage, c.book_value
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        WHERE 1=1
    """
    params = []
    if min_roe is not None:
        query += " AND c.roe_percentage >= ?"
        params.append(min_roe)
    if min_roce is not None:
        query += " AND c.roce_percentage >= ?"
        params.append(min_roce)
    if sector:
        query += " AND s.broad_sector = ?"
        params.append(sector)
    query += " ORDER BY c.roe_percentage DESC"
    
    rows = cursor.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==========================================
# SPRINT 3 PEER COMPARISON API ENDPOINTS
# ==========================================

@app.get("/api/peer-groups", tags=["Sprint 3 Peer Engine"])
def list_peer_groups():
    """Get list of 11 peer groups and member counts."""
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute("""
        SELECT peer_group_name, COUNT(company_id) as member_count
        FROM peer_groups
        GROUP BY peer_group_name
        ORDER BY peer_group_name ASC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/peer/{company_id}", tags=["Sprint 3 Peer Engine"])
def get_company_peer_group(company_id: str):
    """Get peer group information and peer members for a company."""
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute("SELECT peer_group_name, is_benchmark FROM peer_groups WHERE company_id = ?", (company_id.upper(),)).fetchone()
    if not row:
        conn.close()
        return {"company_id": company_id.upper(), "peer_group_name": "No peer group assigned", "members": []}
    
    pg_name = row["peer_group_name"]
    members = cursor.execute("""
        SELECT pg.company_id, pg.is_benchmark, c.company_name, s.broad_sector
        FROM peer_groups pg
        JOIN companies c ON pg.company_id = c.id
        LEFT JOIN sectors s ON c.id = s.company_id
        WHERE pg.peer_group_name = ?
    """, (pg_name,)).fetchall()
    conn.close()
    
    return {
        "company_id": company_id.upper(),
        "peer_group_name": pg_name,
        "is_benchmark": bool(row["is_benchmark"]),
        "members": [dict(m) for m in members]
    }


@app.get("/api/peer/{company_id}/percentiles", tags=["Sprint 3 Peer Engine"])
def get_company_peer_percentiles(company_id: str):
    """Get calculated percentile rankings for a company."""
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM peer_percentiles WHERE company_id = ? ORDER BY metric ASC", (company_id.upper(),)).fetchall()
    conn.close()
    if not rows:
        return {"company_id": company_id.upper(), "status": "No peer group assigned", "percentiles": []}
    return [dict(r) for r in rows]


@app.get("/api/v1/sectors", tags=["Sectors"])
def list_sectors():
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute("""
        SELECT s.broad_sector, 
               COUNT(c.id) as company_count,
               AVG(c.roe_percentage) as avg_roe,
               AVG(c.roce_percentage) as avg_roce
        FROM sectors s
        JOIN companies c ON s.company_id = c.id
        GROUP BY s.broad_sector
        ORDER BY company_count DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
