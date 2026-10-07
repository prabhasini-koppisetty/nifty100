"""
Peer Analytics & Comparison Engine for Nifty 100 Financial Intelligence Platform.
Calculates percentile rankings across 10 required financial metrics within 11 peer groups,
populates SQLite `peer_percentiles` table, generates radar charts, and creates peer_comparison.xlsx.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "db" / "nifty100.db"
OUTPUT_DIR = ROOT_DIR / "output"
REPORTS_DIR = ROOT_DIR / "reports" / "radar_charts"

OUTPUT_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

PEER_EXCEL_PATH = OUTPUT_DIR / "peer_comparison.xlsx"

# 10 Required Percentile Metrics
PEER_METRICS = [
    ("return_on_equity_pct", "ROE", False),
    ("return_on_capital_employed_pct", "ROCE", False),
    ("net_profit_margin_pct", "Net Profit Margin", False),
    ("debt_to_equity", "D/E", True),  # Inverted: lower value = higher percentile
    ("free_cash_flow_cr", "FCF", False),
    ("pat_cagr_5yr", "PAT CAGR 5yr", False),
    ("revenue_cagr_5yr", "Revenue CAGR 5yr", False),
    ("eps_cagr_5yr", "EPS CAGR 5yr", False),
    ("interest_coverage", "Interest Coverage", False),
    ("asset_turnover", "Asset Turnover", False),
]


def load_peer_mappings(db_path: Optional[Path] = None) -> pd.DataFrame:
    """Load peer_groups table from SQLite."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    df_peers = pd.read_sql("SELECT * FROM peer_groups", conn)
    conn.close()
    return df_peers


def calculate_peer_percentiles(df_data: pd.DataFrame, db_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Calculate percentile ranks (0-100 scale) for the 10 required metrics across all 11 peer groups.
    Inverts D/E percentile rank so lower D/E gets higher percentile rank.
    """
    df_peers = load_peer_mappings(db_path)
    
    records = []

    # Merge dataset with peer groups
    merged = pd.merge(df_peers, df_data, left_on="company_id", right_on="company_id", how="inner")

    for pg_name, group in merged.groupby("peer_group_name"):
        for raw_col, metric_label, invert in PEER_METRICS:
            if raw_col not in group.columns:
                continue
                
            vals = group[raw_col].copy()

            for idx, row in group.iterrows():
                cid = row["company_id"]
                val = row[raw_col]
                yr = row.get("year", "2024-03")

                if pd.isna(val):
                    p_rank = np.nan
                else:
                    valid_vals = vals.dropna()
                    if len(valid_vals) <= 1:
                        p_rank = 50.0
                    else:
                        if invert:
                            # Lower value = better percentile
                            rank_count = (valid_vals >= val).sum()
                        else:
                            # Higher value = better percentile
                            rank_count = (valid_vals <= val).sum()
                        p_rank = (rank_count / len(valid_vals)) * 100.0

                records.append({
                    "company_id": cid,
                    "peer_group_name": pg_name,
                    "metric": metric_label,
                    "raw_column": raw_col,
                    "value": round(float(val), 4) if pd.notna(val) else None,
                    "percentile_rank": round(float(p_rank), 2) if pd.notna(p_rank) else None,
                    "year": str(yr)
                })

    df_res = pd.DataFrame(records)
    return df_res


def populate_peer_percentiles_table(df_percentiles: pd.DataFrame, db_path: Optional[Path] = None) -> int:
    """
    Create and populate SQLite peer_percentiles table.
    Ensures foreign keys are enabled and prevents duplicate records.
    """
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON;")

    # Drop and recreate table schema
    create_sql = """
    CREATE TABLE IF NOT EXISTS peer_percentiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT NOT NULL,
        peer_group_name TEXT NOT NULL,
        metric TEXT NOT NULL,
        value REAL,
        percentile_rank REAL,
        year TEXT NOT NULL,
        FOREIGN KEY (company_id) REFERENCES companies(id),
        UNIQUE (company_id, peer_group_name, metric, year)
    );
    """
    conn.execute("DROP TABLE IF EXISTS peer_percentiles;")
    conn.execute(create_sql)

    # Prepare insertion data
    insert_data = []
    for _, r in df_percentiles.iterrows():
        insert_data.append((
            r["company_id"],
            r["peer_group_name"],
            r["metric"],
            r["value"],
            r["percentile_rank"],
            r["year"]
        ))

    insert_sql = """
    INSERT OR REPLACE INTO peer_percentiles (company_id, peer_group_name, metric, value, percentile_rank, year)
    VALUES (?, ?, ?, ?, ?, ?);
    """
    conn.executemany(insert_sql, insert_data)
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM peer_percentiles;").fetchone()[0]
    conn.close()
    return count


def generate_peer_comparison_excel(
    df_data: pd.DataFrame,
    df_percentiles: pd.DataFrame,
    output_path: Optional[Path] = None,
    db_path: Optional[Path] = None
) -> Path:
    """
    Generate output/peer_comparison.xlsx with 11 sheets (1 per peer group).
    
    Formatting:
    - Percentiles: >=75th GREEN (#D1E7DD), 25th-75th YELLOW (#FFF3CD), <=25th RED (#F8D7DA).
    - Benchmark company row: GOLD / AMBER (#FFF2CC) background.
    - Bottom row: Peer Group Median row.
    """
    out_file = output_path or PEER_EXCEL_PATH
    df_peers = load_peer_mappings(db_path)

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default sheet

    # Styling
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    
    benchmark_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
    median_fill = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
    median_font = Font(name="Calibri", size=10, bold=True)

    green_fill = PatternFill(start_color="D1E7DD", end_color="D1E7DD", fill_type="solid")
    yellow_fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
    red_fill = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")

    regular_font = Font(name="Calibri", size=10)
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )

    # 20 KPI/metric columns
    metric_cols = [
        "return_on_equity_pct", "return_on_capital_employed_pct", "operating_profit_margin_pct",
        "net_profit_margin_pct", "debt_to_equity", "interest_coverage", "free_cash_flow_cr",
        "revenue_cagr_3yr", "revenue_cagr_5yr", "pat_cagr_5yr", "eps_cagr_5yr", "asset_turnover",
        "pe_ratio", "pb_ratio", "dividend_yield_pct", "sales", "net_profit",
        "composite_quality_score", "sector_composite_quality_score"
    ]

    p_group_names = sorted(df_peers["peer_group_name"].unique())

    for pg_name in p_group_names:
        # Limit sheet name to 31 chars
        sheet_title = pg_name[:31]
        ws = wb.create_sheet(title=sheet_title)

        pg_members = df_peers[df_peers["peer_group_name"] == pg_name]
        merged_pg = pd.merge(pg_members, df_data, left_on="company_id", right_on="company_id", how="left")

        # Build headers
        headers = ["company_id", "company_name", "broad_sector", "is_benchmark"] + metric_cols
        # Add percentile headers for 10 metrics
        p_headers = [f"{m[1]} Percentile" for m in PEER_METRICS]
        full_headers = headers + p_headers

        ws.append(full_headers)
        for c_idx in range(1, len(full_headers) + 1):
            cell = ws.cell(row=1, column=c_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(full_headers))}{len(merged_pg) + 2}"

        # Write member rows
        row_counter = 2
        for _, row in merged_pg.iterrows():
            cid = row["company_id"]
            is_bm = bool(row.get("is_benchmark", 0))

            row_vals = [
                cid, row.get("company_name"), row.get("broad_sector"), "Yes" if is_bm else "No"
            ]

            # Raw metrics
            for col_n in metric_cols:
                v = row.get(col_n)
                row_vals.append(round(float(v), 2) if pd.notna(v) else None)

            # Percentiles
            cid_pcts = df_percentiles[(df_percentiles["peer_group_name"] == pg_name) & (df_percentiles["company_id"] == cid)]
            pct_map = cid_pcts.set_index("metric")["percentile_rank"].to_dict()

            for _, metric_lbl, _ in PEER_METRICS:
                p_v = pct_map.get(metric_lbl)
                row_vals.append(round(float(p_v), 2) if pd.notna(p_v) else None)

            ws.append(row_vals)

            # Format cells
            for col_idx in range(1, len(full_headers) + 1):
                cell = ws.cell(row=row_counter, column=col_idx)
                cell.font = regular_font
                cell.border = thin_border

                # Benchmark formatting
                if is_bm and col_idx <= 4:
                    cell.fill = benchmark_fill

                # Percentile formatting
                if col_idx > len(headers):
                    val = cell.value
                    if val is not None and isinstance(val, (int, float)):
                        if val >= 75.0:
                            cell.fill = green_fill
                        elif val >= 25.0:
                            cell.fill = yellow_fill
                        else:
                            cell.fill = red_fill

                if col_idx <= 3:
                    cell.alignment = Alignment(horizontal="left")
                else:
                    cell.alignment = Alignment(horizontal="right")

            row_counter += 1

        # Peer Group Median Row
        median_row = ["MEDIAN", "Peer Group Median", "-", "-"]
        for col_n in metric_cols:
            if col_n in merged_pg.columns:
                m_val = merged_pg[col_n].median()
                median_row.append(round(float(m_val), 2) if pd.notna(m_val) else None)
            else:
                median_row.append(None)

        # Percentile medians
        for _, metric_lbl, _ in PEER_METRICS:
            pg_pcts = df_percentiles[(df_percentiles["peer_group_name"] == pg_name) & (df_percentiles["metric"] == metric_lbl)]
            m_p = pg_pcts["percentile_rank"].median()
            median_row.append(round(float(m_p), 2) if pd.notna(m_p) else None)

        ws.append(median_row)
        for col_idx in range(1, len(full_headers) + 1):
            cell = ws.cell(row=row_counter, column=col_idx)
            cell.fill = median_fill
            cell.font = median_font
            cell.border = thin_border
            if col_idx <= 3:
                cell.alignment = Alignment(horizontal="left")
            else:
                cell.alignment = Alignment(horizontal="right")

        # Auto-adjust widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    wb.save(out_file)
    return out_file


def generate_radar_charts(
    df_data: pd.DataFrame,
    df_percentiles: pd.DataFrame,
    output_dir: Optional[Path] = None,
    db_path: Optional[Path] = None
) -> int:
    """
    Generate 8-axis polar radar chart for each company.
    
    8 Axes:
    1. ROE
    2. ROCE
    3. NPM
    4. D/E (inverted)
    5. FCF Score
    6. PAT CAGR 5yr
    7. Revenue CAGR 5yr
    8. Composite Score
    
    Compares company against Peer Group Average (or Nifty 100 average for unassigned companies).
    Saves: reports/radar_charts/<company_id>_radar.png
    """
    out_dir = output_dir or REPORTS_DIR
    df_peers = load_peer_mappings(db_path)

    peer_map = df_peers.groupby("company_id")["peer_group_name"].first().to_dict()

    # 8 Axes specifications
    axes_spec = [
        ("ROE", "return_on_equity_pct", False),
        ("ROCE", "return_on_capital_employed_pct", False),
        ("NPM", "net_profit_margin_pct", False),
        ("D/E Inverted", "debt_to_equity", True),
        ("FCF", "free_cash_flow_cr", False),
        ("PAT CAGR 5yr", "pat_cagr_5yr", False),
        ("Rev CAGR 5yr", "revenue_cagr_5yr", False),
        ("Composite Score", "composite_quality_score", False),
    ]

    labels = [a[0] for a in axes_spec]
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]  # Close circle

    # Compute overall benchmark averages (for companies without a peer group)
    overall_averages = []
    for _, col_name, invert in axes_spec:
        if col_name in df_data.columns:
            vals = df_data[col_name].dropna()
            if len(vals) > 0:
                p10, p90 = vals.quantile(0.10), vals.quantile(0.90)
                norm = (vals.clip(p10, p90) - p10) / (p90 - p10 + 1e-9) * 100.0
                if invert:
                    norm = 100.0 - norm
                overall_averages.append(norm.mean())
            else:
                overall_averages.append(50.0)
        else:
            overall_averages.append(50.0)
    overall_averages += overall_averages[:1]

    chart_count = 0

    for _, row in df_data.iterrows():
        cid = row["company_id"]
        cname = row.get("company_name", cid)
        pg_name = peer_map.get(cid)

        # Extract company 8-axis values (normalized 0-100)
        c_vals = []
        for _, col_name, invert in axes_spec:
            v = row.get(col_name)
            if pd.isna(v):
                c_vals.append(0.0)
            else:
                all_v = df_data[col_name].dropna()
                p10, p90 = all_v.quantile(0.10), all_v.quantile(0.90)
                norm = (np.clip(v, p10, p90) - p10) / (p90 - p10 + 1e-9) * 100.0
                if invert:
                    norm = 100.0 - norm
                c_vals.append(norm)

        c_vals += c_vals[:1]

        # Peer average values
        if pg_name:
            pg_cids = df_peers[df_peers["peer_group_name"] == pg_name]["company_id"].tolist()
            pg_df = df_data[df_data["company_id"].isin(pg_cids)]
            pg_avg_vals = []
            for _, col_name, invert in axes_spec:
                vals = pg_df[col_name].dropna()
                if len(vals) > 0:
                    p10, p90 = df_data[col_name].quantile(0.10), df_data[col_name].quantile(0.90)
                    norm = (vals.clip(p10, p90) - p10) / (p90 - p10 + 1e-9) * 100.0
                    if invert:
                        norm = 100.0 - norm
                    pg_avg_vals.append(norm.mean())
                else:
                    pg_avg_vals.append(50.0)
            pg_avg_vals += pg_avg_vals[:1]
            ref_label = f"Peer Avg ({pg_name})"
        else:
            pg_avg_vals = overall_averages
            ref_label = "Nifty 100 Benchmark Avg"

        # Plot radar chart
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        
        # Company polygon
        ax.plot(angles, c_vals, color="#1E3A8A", linewidth=2.5, label=f"{cid}")
        ax.fill(angles, c_vals, color="#3B82F6", alpha=0.3)

        # Peer / Benchmark line
        ax.plot(angles, pg_avg_vals, color="#EF4444", linewidth=2, linestyle="--", label=ref_label)

        # Formatting
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=9, fontweight="bold", color="#1E293B")
        ax.set_rlabel_position(0)
        plt.yticks([25, 50, 75, 100], ["25", "50", "75", "100"], color="#64748B", size=8)
        plt.ylim(0, 100)

        plt.title(f"{cname} ({cid})\nPeer Radar Performance Profile", fontsize=11, fontweight="bold", pad=20, color="#0F172A")
        plt.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=8)

        img_path = out_dir / f"{cid}_radar.png"
        plt.savefig(img_path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        chart_count += 1

    return chart_count


def run_peer_engine(df_data: pd.DataFrame, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Execute complete peer analytics pipeline."""
    df_percentiles = calculate_peer_percentiles(df_data, db_path)
    table_count = populate_peer_percentiles_table(df_percentiles, db_path)
    excel_path = generate_peer_comparison_excel(df_data, df_percentiles, db_path=db_path)
    radar_count = generate_radar_charts(df_data, df_percentiles, db_path=db_path)

    return {
        "peer_percentiles_rows": table_count,
        "peer_comparison_excel": str(excel_path),
        "radar_charts_generated": radar_count
    }


if __name__ == "__main__":
    from src.screener.engine import load_financial_data
    print("Testing Peer Comparison Engine...")
    df_fin = load_financial_data()
    res = run_peer_engine(df_fin)
    for k, v in res.items():
        print(f"{k}: {v}")
