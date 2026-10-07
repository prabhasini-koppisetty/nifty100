# Bluestock Nifty 100 Financial Intelligence Platform

## Overview
The **Bluestock Nifty 100 Financial Intelligence Platform** is an end-to-end data engineering, ETL, and fundamental financial analytics platform analyzing Nifty 100 corporate financial statements in India.

This codebase covers:
- **Sprint 1**: Data ingestion, normalization, validation, and SQLite database loading.
- **Sprint 2**: **Financial Ratio Engine**, CAGR calculation engine, cash-flow KPI analytics, capital allocation pattern classifier, and 0–100 composite quality scoring.
- **Sprint 3**: **Financial Screener & Peer Comparison Engine**, analyst-editable preset screeners, custom threshold filtering, P10/P90 winsorisation, 11-group peer percentiles, polar radar charts, automated Excel workbooks, and REST API / Streamlit UI integration.

---

## Sprint 3: Financial Screener & Peer Comparison Engine Architecture

Sprint 3 implements an analytical screening and peer benchmarking framework on top of the Sprint 1 & Sprint 2 data warehouse.

### Submodules & Components
1. **`config/screener_config.yaml`**: Analyst-editable configuration file defining criteria for the 6 preset screeners and specifications for 15 filterable metrics.
2. **`src/screener/engine.py`**: Modular screener engine implementing threshold filters, preset execution, P10/P90 winsorised composite quality scoring, sector-relative score calculations, and Excel report generation (`output/screener_output.xlsx`).
3. **`src/analytics/peer.py`**: Peer comparison engine calculating percentile ranks (0–100 scale) for 10 financial metrics across 11 peer groups, populating the SQLite `peer_percentiles` table, generating 8-axis polar radar charts (`reports/radar_charts/<company_id>_radar.png`), and creating the peer comparison workbook (`output/peer_comparison.xlsx`).
4. **`src/api/main.py`**: REST API endpoints for presets (`GET /api/screener/presets`), custom screening (`POST /api/screener/custom`), peer groups (`GET /api/peer-groups`), and percentiles (`GET /api/peer/{company_id}/percentiles`).
5. **`src/dashboard/app.py`**: Streamlit dashboard incorporating the interactive Screener runner and Peer Comparison radar viewer.

---

## 15 Filterable Metrics & Special Rules

The screener engine supports filtering across 15 core fundamental metrics:

1. **ROE Minimum** (`return_on_equity_pct`)
2. **D/E Maximum** (`debt_to_equity`) — **Financials Carve-Out Rule**: Companies in the `Financials` broad sector automatically bypass D/E max restrictions due to structural banking leverage.
3. **FCF Minimum** (`free_cash_flow_cr`)
4. **Revenue CAGR 5yr Minimum** (`revenue_cagr_5yr`)
5. **PAT CAGR 5yr Minimum** (`pat_cagr_5yr`)
6. **OPM Minimum** (`operating_profit_margin_pct`)
7. **P/E Maximum** (`pe_ratio`)
8. **P/B Maximum** (`pb_ratio`)
9. **Dividend Yield Minimum** (`dividend_yield_pct`)
10. **ICR Minimum** (`interest_coverage`) — **Debt-Free Rule**: Companies with `icr_label == 'Debt Free'` treat ICR as infinity ($\infty$) and always pass ICR minimum thresholds.
11. **Market Cap Minimum** (`market_cap_crore`)
12. **Net Profit Minimum** (`net_profit`)
13. **EPS CAGR Minimum** (`eps_cagr_5yr`)
14. **Asset Turnover Minimum** (`asset_turnover`)
15. **Sales Minimum** (`sales`)

---

## Six Preset Screeners & Results

| Preset Name | Description / Business Criteria | Matching Companies Count | Top 3 Matching Companies |
| :--- | :--- | :---: | :--- |
| **1. Quality Compounder** | ROE > 15%, D/E < 1.0, FCF > 0, Rev CAGR 5yr > 10% | **22** | TCS, INFY, HCLTECH |
| **2. Value Pick** | P/E < 20, P/B < 3.0, D/E < 2.0, Dividend Yield > 1% | **2** | COALINDIA, NTPC |
| **3. Growth Accelerator** | PAT CAGR 5yr > 20%, Rev CAGR 5yr > 15%, D/E < 2.0 | **19** | TRENT, ADANIPORTS, INDIGO |
| **4. Dividend Champion** | Div Yield > 2%, Div Payout < 80%, FCF > 0 | **30** | HCLTECH, COALINDIA, POWERGRID |
| **5. Debt-Free Blue Chip** | D/E = 0, ROE > 12%, Sales > 5000 Crore | **18** | TCS, INFY, COALINDIA |
| **6. Turnaround Watch** | Rev CAGR 3yr > 10%, FCF > 0, D/E declining YoY | **3** | ADANIPOWER, TATAMOTORS, JSWSTEEL |

---

## Composite Quality Score & Winsorisation Methodology

The 100-point Sprint 3 Composite Quality Score evaluates four analytical pillars:

1. **Profitability (35%)**: ROE (15%), ROCE (10%), NPM (10%).
2. **Cash Quality (30%)**: FCF Value/Growth (15%), CFO/PAT Ratio (10%), FCF Positive Flag (5%).
3. **Growth (20%)**: Revenue CAGR 5yr (10%), PAT CAGR 5yr (10%).
4. **Leverage (15%)**: Debt-to-Equity (10% — inverted score), Interest Coverage Ratio (5%).

### P10 / P90 Winsorisation & Normalization
To prevent extreme financial outliers from distorting rankings:
1. Calculate 10th percentile ($P_{10}$) and 90th percentile ($P_{90}$) across the company universe.
2. Clip values below $P_{10}$ to $P_{10}$ and above $P_{90}$ to $P_{90}$.
3. Normalize to a 0–100 scale:
   $$\text{Score} = \frac{x - P_{10}}{P_{90} - P_{10}} \times 100$$
4. For metrics where lower is better (D/E), invert the score ($100 - \text{Score}$).

### Sector-Relative Score
In addition to the overall composite score, `sector_composite_quality_score` computes winsorisation and normalization within each company's `broad_sector` group to ensure fair comparison among sector peers.

---

## Peer Percentile Methodology & Inverse Ranking

### 11 Peer Groups & 56 Mapped Companies
Peer groups evaluated: *Automobiles, Consumer Finance, FMCG, IT Services, Life Insurance, Oil & Gas, Pharmaceuticals, Power & Utilities, Private Banks, Public Sector Banks, Steel*.

### 10 Required Percentile Metrics
ROE, ROCE, Net Profit Margin, D/E, FCF, PAT CAGR 5yr, Revenue CAGR 5yr, EPS CAGR 5yr, Interest Coverage, Asset Turnover.

### Inverse D/E Percentile Logic
For normal metrics, higher values yield higher percentile ranks. For **Debt-to-Equity**, lower values indicate superior solvency; therefore, percentile ranks are inverted so that the company with the lowest D/E receives the 100th percentile rank.

### SQLite Table: `peer_percentiles`
560 records populated with schema: `(company_id, peer_group_name, metric, value, percentile_rank, year)`.

---

## 8-Axis Polar Radar Charts (`reports/radar_charts/`)

Generates 8-axis polar radar charts for all 92 companies saved as `reports/radar_charts/<company_id>_radar.png`.

**8 Axes**: ROE, ROCE, NPM, D/E (inverted), FCF, PAT CAGR 5yr, Rev CAGR 5yr, Composite Score.

- **Company Profile**: Solid blue polygon (`#1E3A8A`).
- **Reference Benchmark**: Dashed red polygon (`#EF4444`) representing the Peer Group Average (or Nifty 100 Benchmark Average for unmapped companies).

---

## Automated Excel Reports

1. **`output/screener_output.xlsx`**: Exactly 6 sheets (one per preset). Features header freezing, dark blue header formatting, auto-fit column widths, autofilters, and cell color coding (**Green** = meets threshold, **Red** = fails threshold). Sorted DESC by composite score.
2. **`output/peer_comparison.xlsx`**: Exactly 11 sheets (one per peer group). Features percentile conditional formatting ($\ge 75\text{th}$ **Green**, $25\text{th}–75\text{th}$ **Yellow**, $\le 25\text{th}$ **Red**), **Gold/Amber** benchmark company row highlight, and a **Peer Group Median** summary row at the bottom.

---

## Verification & Validation Summary

| Validation Check | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- |
| **Pytest Test Suite** | 97 passed | **97 passed** in 6.18s | ✅ Pass |
| **SQLite Foreign Key Check** | 0 errors | **0 rows** (`PRAGMA foreign_key_check`) | ✅ Pass |
| **Duplicate Percentiles Check** | 0 duplicates | **0 duplicates** | ✅ Pass |
| **`peer_percentiles` Row Count** | 560 rows | **560 rows** | ✅ Pass |
| **IT Services ROE Percentiles** | TCS = 100th, TECHM = 20th | TCS (50.9%)=100.0, TECHM (9.0%)=20.0 | ✅ Pass |
| **IT Services D/E Inverse Rank**| Lower D/E = Higher Rank | HCLTECH (0.084 D/E) = 100.0 Rank | ✅ Pass |
| **`screener_output.xlsx` Sheets** | 6 sheets | **6 sheets** | ✅ Pass |
| **`peer_comparison.xlsx` Sheets** | 11 sheets | **11 sheets** | ✅ Pass |
| **Radar PNG Charts** | 92 files | **92 files** generated | ✅ Pass |

---

## Known Limitations
1. **Unassigned Peer Group Companies**: 36 companies in the Nifty 100 universe are not assigned to the 11 specific peer groups; their radar charts fallback to comparing against the Nifty 100 universe average.
2. **Interim Period Data**: Interim periods (e.g. `2024-09`) with missing annual metrics are automatically filtered out in favor of the latest complete annual fiscal period (`2024-03`).

---

## Execution Commands

Run Screener Engine:
```bash
.venv\Scripts\python.exe src/screener/engine.py
```

Run Peer Analytics Engine:
```bash
.venv\Scripts\python.exe src/analytics/peer.py
```

Run Full Test Suite:
```bash
.venv\Scripts\python.exe -m pytest -q
```

Run FastAPI Backend:
```bash
.venv\Scripts\uvicorn.exe src.api.main:app --reload
```

Run Streamlit Dashboard:
```bash
.venv\Scripts\streamlit.exe run src/dashboard/app.py
```
