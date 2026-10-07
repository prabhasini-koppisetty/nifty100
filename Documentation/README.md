# Bluestock Nifty 100 Financial Intelligence Platform

## Overview
The **Bluestock Nifty 100 Financial Intelligence Platform** is an end-to-end data engineering, ETL, and financial analytics solution for analyzing Nifty 100 corporate financial statements in India.

This codebase covers:
- **Sprint 1**: Data ingestion, normalization, validation, and SQLite loading.
- **Sprint 2**: **Financial Ratio Engine**, CAGR calculation engine, cash-flow KPI analytics, capital allocation pattern classifier, and composite quality scoring.

---

## Sprint 2: Financial Ratio Engine Architecture

Sprint 2 builds a high-performance, modular analytics layer on top of Sprint 1 data tables. It computes 50+ Key Performance Indicators (KPIs) for all 92 Nifty 100 companies across all available financial years.

### Analytics Submodules (`src/analytics/`)
1. **`src/analytics/ratios.py`**: Profitability, Leverage, and Efficiency Ratios.
2. **`src/analytics/cagr.py`**: CAGR Engine with multi-year growth & edge-case flags.
3. **`src/analytics/cashflow_kpis.py`**: Cash flow metrics, CFO quality scoring, CapEx intensity, and capital allocation classifier.
4. **`src/analytics/quality_score.py`**: Transparent 0–100 Composite Quality Score.
5. **`src/analytics/engine.py`**: Main pipeline orchestrator that populates SQLite and generates output files.

---

## Key Formulas & Methodology

### 1. Profitability Ratios
- **Net Profit Margin (%)**: `(net_profit / sales) * 100` *(Returns `None` if sales is zero)*
- **Operating Profit Margin (%)**: `(operating_profit / sales) * 100` *(Cross-checked against source OPM; logs mismatch if diff > 1%)*
- **Return on Equity (%)**: `(net_profit / (equity_capital + reserves)) * 100` *(Returns `None` if equity + reserves <= 0)*
- **Return on Capital Employed (%)**: `(EBIT / (equity_capital + reserves + borrowings)) * 100` where `EBIT = profit_before_tax + interest`
- **Return on Assets (%)**: `(net_profit / total_assets) * 100` *(Returns `None` if total_assets <= 0)*

### 2. Leverage & Efficiency Ratios
- **Debt-to-Equity**: `borrowings / (equity_capital + reserves)` *(Returns `0.0` if borrowings == 0; `None` if equity <= 0)*
- **High Leverage Flag**: `True` if `D/E > 5` AND company is NOT in `Financials` broad sector.
- **Interest Coverage Ratio (ICR)**: `(operating_profit + other_income) / interest` *(Returns `None` if interest == 0)*
- **ICR Label**: `"Debt Free"` if company has zero interest / zero borrowings and ICR is `None`.
- **ICR Warning Flag**: `True` if `ICR < 1.5` (and ICR is not None).
- **Net Debt (Cr)**: `borrowings - investments` *(Uses investments as liquid asset proxy)*
- **Asset Turnover**: `sales / total_assets`

### 3. Financials Sector Carve-Out
- Financial services companies (23 companies in `Financials` broad sector) operate with high structural leverage.
- Standard `high_leverage_flag` warning is suppressed for Financials companies.
- Source benchmark ROCE and ROE from `companies.xlsx` are cross-checked. Discrepancies > 5% are logged to `output/ratio_edge_cases.log` without overwriting the authoritative ratio-engine values.

---

## CAGR Engine & Edge Cases (`src/analytics/cagr.py`)

Formula:
$$\text{CAGR} = \left( \left( \frac{\text{End Value}}{\text{Start Value}} \right)^{\frac{1}{n}} - 1 \right) \times 100$$

Calculates 3-year, 5-year, and 10-year growth rates for **Revenue**, **PAT**, and **EPS**.

### Edge-Case Handling & Flags:
1. **`NORMAL`**: Positive -> Positive value (calculated normally).
2. **`DECLINE_TO_LOSS`**: Positive -> Negative (returns `None`).
3. **`TURNAROUND`**: Negative -> Positive (returns `None`).
4. **`BOTH_NEGATIVE`**: Negative -> Negative (returns `None`).
5. **`ZERO_BASE`**: Start value == 0 (returns `None`).
6. **`INSUFFICIENT`**: Fewer than $n$ years of available historical data (returns `None`).

---

## Cash Flow KPIs & Capital Allocation Patterns (`src/analytics/cashflow_kpis.py`)

- **Free Cash Flow (FCF Cr)**: `operating_activity + investing_activity`
- **CFO Quality Score**: 5-year rolling average of `CFO / PAT`.
  - `> 1.0`: High Quality
  - `0.5 to 1.0`: Moderate
  - `< 0.5`: Accrual Risk
- **CapEx Intensity (%)**: `abs(investing_activity) / sales * 100`
  - `< 3%`: Asset Light
  - `3%–8%`: Moderate
  - `> 8%`: Capital Intensive
- **FCF Conversion Rate (%)**: `(FCF / operating_profit) * 100`

### Capital Allocation Classifier
Classifies company-year cash flow patterns based on signs of CFO ($+$ or $-$), CFI ($+$ or $-$), and CFF ($+$ or $-$):
- `(+,-,-)` with high CFO/PAT ($> 1.0$): **Shareholder Returns**
- `(+,-,-)` otherwise: **Reinvestor**
- `(+,+,-)`: **Liquidating Assets**
- `(-,+,+)`: **Distress Signal**
- `(-,-,+)`: **Growth Funded by Debt**
- `(+,+,+)`: **Cash Accumulator**
- `(-,-,-)`: **Pre-Revenue**
- `(+,-,+)`: **Mixed**

Generated file: `output/capital_allocation.csv` (1056 rows).

---

## Composite Quality Score (0–100) (`src/analytics/quality_score.py`)

Scoring Breakdown:
1. **Profitability (Max 30 pts)**: NPM (>15%: 10pts, 5-15%: 5pts), ROE (>15%: 10pts, 5-15%: 5pts), ROCE (>15%: 10pts, 5-15%: 5pts).
2. **Cash Flow Quality (Max 30 pts)**: CFO Quality Score (>1.0: 15pts, 0.5-1.0: 8pts), FCF Conversion (>80%: 15pts, 40-80%: 8pts).
3. **Solvency (Max 20 pts)**: D/E (<0.5 or Debt Free: 10pts, 0.5-1.5: 5pts), ICR (>3.0 or Debt Free: 10pts, 1.5-3.0: 5pts).
4. **Growth (Max 20 pts)**: 5-yr Revenue CAGR (>10%: 10pts, 0-10%: 5pts), 5-yr PAT CAGR (>10%: 10pts, 0-10%: 5pts).

*Proportionally normalizes score when optional KPIs are missing.*

---

## Verification & Validation Summary

1. **Test Results**: **67 passed in 0.89s** (26 KPI tests + 41 ETL tests, 0 failures).
2. **`financial_ratios` Table Row Count**: **1,155 rows** (Target: $\ge 1100$).
3. **Distinct Company Count**: **92 companies**.
4. **Duplicate `(company_id, year)` Check**: **0 duplicates**.
5. **Foreign Key Integrity**: **0 violations** (`PRAGMA foreign_key_check`).
6. **KPI Columns**: **44 KPI columns**, 0 NULL-only columns.
7. **3-Company Manual Spot Check**: `< 0.0001%` difference (< 0.1% target) for ABB, TCS, RELIANCE.

---

## Execution Commands

Run ratio engine pipeline:
```bash
$env:PYTHONPATH="."
python src/analytics/engine.py
```

Run test suite:
```bash
$env:PYTHONPATH="."
python -m pytest
```
