"""
Sprint 2 Financial Ratio Engine - Main Pipeline Orchestrator.
Calculates 50+ KPIs for all 92 companies across all available financial years.
Populates SQLite `financial_ratios` table and writes output reports:
- output/capital_allocation.csv
- output/ratio_edge_cases.log
"""

import sqlite3
import logging
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

from src.analytics.ratios import (
    calculate_net_profit_margin,
    calculate_operating_profit_margin,
    calculate_return_on_equity,
    calculate_return_on_capital_employed,
    calculate_return_on_assets,
    calculate_debt_to_equity,
    calculate_high_leverage_flag,
    calculate_interest_coverage,
    calculate_icr_label,
    calculate_icr_warning_flag,
    calculate_net_debt,
    calculate_asset_turnover,
)
from src.analytics.cagr import calculate_cagr, calculate_series_cagr
from src.analytics.cashflow_kpis import (
    calculate_free_cash_flow,
    calculate_cfo_quality_score,
    calculate_capex_intensity,
    calculate_fcf_conversion,
    classify_capital_allocation,
)
from src.analytics.quality_score import calculate_composite_quality_score

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "db" / "nifty100.db"
OUTPUT_DIR = ROOT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

CAPITAL_ALLOCATION_CSV = OUTPUT_DIR / "capital_allocation.csv"
EDGE_CASES_LOG = OUTPUT_DIR / "ratio_edge_cases.log"

logger = logging.getLogger("ratio_engine")
logging.basicConfig(level=logging.INFO)


def run_ratio_engine(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    Main execution pipeline for Sprint 2 Financial Ratio Engine.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    # 1. Load Data
    companies_df = pd.read_sql("SELECT * FROM companies", conn)
    sectors_df = pd.read_sql("SELECT * FROM sectors", conn)
    pl_df = pd.read_sql("SELECT * FROM profitandloss", conn)
    bs_df = pd.read_sql("SELECT * FROM balancesheet", conn)
    cf_df = pd.read_sql("SELECT * FROM cashflow", conn)

    # Pre-map company sector and metadata
    comp_meta = {}
    for _, row in companies_df.iterrows():
        cid = str(row["id"]).strip().upper()
        comp_meta[cid] = {
            "name": row.get("company_name"),
            "book_value": row.get("book_value"),
            "roce_src": row.get("roce_percentage"),
            "roe_src": row.get("roe_percentage"),
        }

    fin_sectors = set()
    for _, row in sectors_df.iterrows():
        cid = str(row["company_id"]).strip().upper()
        b_sec = str(row.get("broad_sector", "")).strip()
        if b_sec == "Financials":
            fin_sectors.add(cid)

    # Get union of all company-year pairs
    all_pairs_query = """
    SELECT company_id, year FROM profitandloss
    UNION
    SELECT company_id, year FROM balancesheet
    UNION
    SELECT company_id, year FROM cashflow
    """
    all_pairs_df = pd.read_sql(all_pairs_query, conn)
    all_pairs_df["company_id"] = all_pairs_df["company_id"].str.strip().str.upper()

    # Index financial data for fast lookup
    pl_dict = pl_df.set_index(["company_id", "year"]).to_dict("index")
    bs_dict = bs_df.set_index(["company_id", "year"]).to_dict("index")
    cf_dict = cf_df.set_index(["company_id", "year"]).to_dict("index")

    # Time-series dictionary for CAGR per company
    company_time_series = {}
    for cid in all_pairs_df["company_id"].unique():
        company_time_series[cid] = {"sales": {}, "net_profit": {}, "eps": {}}

    for (cid, yr), row in pl_dict.items():
        if cid not in company_time_series:
            company_time_series[cid] = {"sales": {}, "net_profit": {}, "eps": {}}
        company_time_series[cid]["sales"][yr] = row.get("sales")
        company_time_series[cid]["net_profit"][yr] = row.get("net_profit")
        company_time_series[cid]["eps"][yr] = row.get("eps")

    ratio_rows = []
    cap_alloc_rows = []
    edge_cases = []

    # Iterate over all company-year combinations
    for _, row in all_pairs_df.iterrows():
        cid = row["company_id"]
        yr = row["year"]
        is_financial = cid in fin_sectors
        meta = comp_meta.get(cid, {})

        pl_row = pl_dict.get((cid, yr), {})
        bs_row = bs_dict.get((cid, yr), {})
        cf_row = cf_dict.get((cid, yr), {})

        # Extract primary metrics
        sales = pl_row.get("sales")
        op_profit = pl_row.get("operating_profit")
        source_opm = pl_row.get("opm_percentage")
        other_inc = pl_row.get("other_income")
        interest = pl_row.get("interest")
        pbt = pl_row.get("profit_before_tax")
        net_profit = pl_row.get("net_profit")
        eps = pl_row.get("eps")
        div_payout = pl_row.get("dividend_payout")

        eq_capital = bs_row.get("equity_capital")
        reserves = bs_row.get("reserves")
        borrowings = bs_row.get("borrowings")
        investments = bs_row.get("investments")
        total_assets = bs_row.get("total_assets")

        cfo = cf_row.get("operating_activity")
        cfi = cf_row.get("investing_activity")
        cff = cf_row.get("financing_activity")

        # 1. Profitability Ratios
        npm = calculate_net_profit_margin(net_profit, sales)
        opm = calculate_operating_profit_margin(
            op_profit, sales, source_opm=source_opm, company_id=cid, year=yr
        )
        roe = calculate_return_on_equity(net_profit, eq_capital, reserves)

        ebit = (pbt + interest) if (pbt is not None and interest is not None) else None
        if ebit is None and op_profit is not None:
            ebit = op_profit + (other_inc if other_inc is not None else 0.0)
        roce = calculate_return_on_capital_employed(
            ebit, eq_capital, reserves, borrowings, is_financial=is_financial
        )
        roa = calculate_return_on_assets(net_profit, total_assets)

        # 2. Leverage & Efficiency Ratios
        de = calculate_debt_to_equity(borrowings, eq_capital, reserves)
        high_lev_flag = calculate_high_leverage_flag(de, is_financial=is_financial)
        icr = calculate_interest_coverage(op_profit, other_inc, interest)
        icr_lbl = calculate_icr_label(icr, interest=interest, borrowings=borrowings)
        icr_warn = calculate_icr_warning_flag(icr)
        net_debt = calculate_net_debt(borrowings, investments)
        asset_turnover = calculate_asset_turnover(sales, total_assets)

        # 3. Cash Flow KPIs
        fcf = calculate_free_cash_flow(cfo, cfi)
        capex_cr = abs(cfi) if cfi is not None else None

        # 5-year rolling CFO & PAT for CFO Quality Score
        avail_years = sorted([y for y in company_time_series[cid]["net_profit"].keys() if y <= yr])[-5:]
        cfo_list = [cf_dict.get((cid, y), {}).get("operating_activity") for y in avail_years]
        pat_list = [pl_dict.get((cid, y), {}).get("net_profit") for y in avail_years]

        cfo_qual_score, cfo_qual_class = calculate_cfo_quality_score(cfo_list, pat_list)
        capex_int_pct, capex_int_class = calculate_capex_intensity(cfi, sales)
        fcf_conv = calculate_fcf_conversion(fcf, op_profit)

        # Capital Allocation Classifier
        cfo_sign, cfi_sign, cff_sign, pattern_lbl = classify_capital_allocation(
            cfo, cfi, cff, cfo_pat_ratio=cfo_qual_score
        )
        if cfo is not None and cfi is not None and cff is not None:
            cap_alloc_rows.append({
                "company_id": cid,
                "year": yr,
                "cfo_sign": cfo_sign,
                "cfi_sign": cfi_sign,
                "cff_sign": cff_sign,
                "pattern_label": pattern_lbl
            })

        # 4. Multi-year CAGR Engine
        rev_3yr, rev_3yr_flag = calculate_series_cagr(company_time_series[cid]["sales"], yr, 3)
        rev_5yr, rev_5yr_flag = calculate_series_cagr(company_time_series[cid]["sales"], yr, 5)
        rev_10yr, rev_10yr_flag = calculate_series_cagr(company_time_series[cid]["sales"], yr, 10)

        pat_3yr, pat_3yr_flag = calculate_series_cagr(company_time_series[cid]["net_profit"], yr, 3)
        pat_5yr, pat_5yr_flag = calculate_series_cagr(company_time_series[cid]["net_profit"], yr, 5)
        pat_10yr, pat_10yr_flag = calculate_series_cagr(company_time_series[cid]["net_profit"], yr, 10)

        eps_3yr, eps_3yr_flag = calculate_series_cagr(company_time_series[cid]["eps"], yr, 3)
        eps_5yr, eps_5yr_flag = calculate_series_cagr(company_time_series[cid]["eps"], yr, 5)
        eps_10yr, eps_10yr_flag = calculate_series_cagr(company_time_series[cid]["eps"], yr, 10)

        # 5. Composite Quality Score
        qual_score = calculate_composite_quality_score(
            npm=npm,
            roe=roe,
            roce=roce,
            cfo_quality_score=cfo_qual_score,
            fcf_conversion=fcf_conv,
            debt_to_equity=de,
            icr=icr,
            icr_label=icr_lbl,
            revenue_cagr_5yr=rev_5yr,
            pat_cagr_5yr=pat_5yr
        )

        # 6. Edge Case Checks against Source Meta
        src_roce = meta.get("roce_src")
        src_roe = meta.get("roe_src")

        # Check latest year ROCE & ROE against companies source
        latest_yr = sorted(all_pairs_df[all_pairs_df["company_id"] == cid]["year"])[-1]
        if yr == latest_yr:
            if roce is not None and src_roce is not None:
                diff_roce = abs(roce - src_roce)
                if diff_roce > 5.0:
                    edge_cases.append({
                        "company_id": cid,
                        "company_name": meta.get("name", "N/A"),
                        "year": yr,
                        "metric": "ROCE",
                        "computed_value": round(roce, 2),
                        "source_value": round(src_roce, 2),
                        "difference": round(diff_roce, 2),
                        "category": "FORMULA_DISCREPANCY" if not is_financial else "VERSION_DIFFERENCE",
                        "explanation": f"Computed annual ROCE ({roce:.2f}%) differs from companies.xlsx benchmark ROCE ({src_roce:.2f}%). {'Financials sector leverage model difference.' if is_financial else 'Difference in TTM/latest period vs annual EBIT calculation.'}"
                    })

            if roe is not None and src_roe is not None:
                diff_roe = abs(roe - src_roe)
                if diff_roe > 5.0:
                    edge_cases.append({
                        "company_id": cid,
                        "company_name": meta.get("name", "N/A"),
                        "year": yr,
                        "metric": "ROE",
                        "computed_value": round(roe, 2),
                        "source_value": round(src_roe, 2),
                        "difference": round(diff_roe, 2),
                        "category": "VERSION_DIFFERENCE",
                        "explanation": f"Computed annual ROE ({roe:.2f}%) differs from companies.xlsx benchmark ROE ({src_roe:.2f}%). Authoritative ratio-engine value retained."
                    })

        ratio_rows.append({
            "company_id": cid,
            "year": yr,
            "net_profit_margin_pct": npm,
            "operating_profit_margin_pct": opm,
            "return_on_equity_pct": roe,
            "return_on_capital_employed_pct": roce,
            "return_on_assets_pct": roa,
            "debt_to_equity": de,
            "high_leverage_flag": 1 if high_lev_flag else 0,
            "interest_coverage": icr,
            "icr_label": icr_lbl,
            "icr_warning_flag": 1 if icr_warn else 0,
            "net_debt_cr": net_debt,
            "asset_turnover": asset_turnover,
            "free_cash_flow_cr": fcf,
            "capex_cr": capex_cr,
            "earnings_per_share": eps,
            "book_value_per_share": meta.get("book_value"),
            "dividend_payout_ratio_pct": div_payout,
            "total_debt_cr": borrowings,
            "cash_from_operations_cr": cfo,
            "cfo_quality_score": cfo_qual_score,
            "cfo_quality_classification": cfo_qual_class,
            "capex_intensity_pct": capex_int_pct,
            "capex_intensity_classification": capex_int_class,
            "fcf_conversion_pct": fcf_conv,
            "capital_allocation_pattern": pattern_lbl,
            "revenue_cagr_3yr": rev_3yr,
            "revenue_cagr_3yr_flag": rev_3yr_flag,
            "revenue_cagr_5yr": rev_5yr,
            "revenue_cagr_5yr_flag": rev_5yr_flag,
            "revenue_cagr_10yr": rev_10yr,
            "revenue_cagr_10yr_flag": rev_10yr_flag,
            "pat_cagr_3yr": pat_3yr,
            "pat_cagr_3yr_flag": pat_3yr_flag,
            "pat_cagr_5yr": pat_5yr,
            "pat_cagr_5yr_flag": pat_5yr_flag,
            "pat_cagr_10yr": pat_10yr,
            "pat_cagr_10yr_flag": pat_10yr_flag,
            "eps_cagr_3yr": eps_3yr,
            "eps_cagr_3yr_flag": eps_3yr_flag,
            "eps_cagr_5yr": eps_5yr,
            "eps_cagr_5yr_flag": eps_5yr_flag,
            "eps_cagr_10yr": eps_10yr,
            "eps_cagr_10yr_flag": eps_10yr_flag,
            "composite_quality_score": qual_score,
        })

    # Export output/capital_allocation.csv
    cap_alloc_df = pd.DataFrame(cap_alloc_rows)
    cap_alloc_df.to_csv(CAPITAL_ALLOCATION_CSV, index=False)

    # Export output/ratio_edge_cases.log
    with open(EDGE_CASES_LOG, "w", encoding="utf-8") as f:
        f.write("=== SPRINT 2 RATIO ENGINE EDGE CASE & ANOMALY LOG ===\n\n")
        for ec in edge_cases:
            f.write(
                f"Company ID: {ec['company_id']} ({ec['company_name']}) | Year: {ec['year']}\n"
                f"Metric: {ec['metric']} | Computed: {ec['computed_value']} | Source: {ec['source_value']} | Diff: {ec['difference']}\n"
                f"Category: {ec['category']} | Explanation: {ec['explanation']}\n"
                f"{'-'*80}\n"
            )

    # Repopulate SQLite financial_ratios table
    ratio_df = pd.DataFrame(ratio_rows)

    # Recreate financial_ratios table using schema.sql definition to ensure all Sprint 2 columns exist
    schema_sql = (ROOT_DIR / "db" / "schema.sql").read_text(encoding="utf-8")
    conn.execute("DROP TABLE IF EXISTS financial_ratios;")
    conn.executescript(schema_sql)

    ratio_df.to_sql("financial_ratios", conn, if_exists="append", index=False)
    conn.commit()

    # Verification queries
    total_rows = conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
    distinct_comps = conn.execute("SELECT COUNT(DISTINCT company_id) FROM financial_ratios").fetchone()[0]

    conn.close()

    return {
        "financial_ratios_rows": total_rows,
        "distinct_companies": distinct_comps,
        "capital_allocation_rows": len(cap_alloc_df),
        "edge_case_anomalies": len(edge_cases),
        "financials_count": len(fin_sectors),
    }


if __name__ == "__main__":
    res = run_ratio_engine()
    print("\n=== RATIO ENGINE EXECUTION SUMMARY ===")
    for k, v in res.items():
        print(f"{k}: {v}")
