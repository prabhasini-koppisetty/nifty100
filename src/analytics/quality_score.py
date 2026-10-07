"""
Transparent Composite Quality Score (0 - 100) model for Nifty 100 companies.
Evaluates Profitability, Cash Flow Quality, Balance Sheet Solvency, and Growth.
Proportionally scales score when optional KPIs are missing.
"""

from typing import Optional, Dict, Any


def calculate_composite_quality_score(
    npm: Optional[float] = None,
    roe: Optional[float] = None,
    roce: Optional[float] = None,
    cfo_quality_score: Optional[float] = None,
    fcf_conversion: Optional[float] = None,
    debt_to_equity: Optional[float] = None,
    icr: Optional[float] = None,
    icr_label: Optional[str] = None,
    revenue_cagr_5yr: Optional[float] = None,
    pat_cagr_5yr: Optional[float] = None
) -> Optional[float]:
    """
    Calculate Composite Quality Score (0-100).

    Scoring Methodology:
    1. Profitability (Max 30 pts):
       - NPM > 15%: 10 pts, 5-15%: 5 pts
       - ROE > 15%: 10 pts, 5-15%: 5 pts
       - ROCE > 15%: 10 pts, 5-15%: 5 pts

    2. Cash Flow Quality (Max 30 pts):
       - CFO Quality Score > 1.0: 15 pts, 0.5-1.0: 8 pts
       - FCF Conversion Rate > 80%: 15 pts, 40-80%: 8 pts, > 0%: 4 pts

    3. Solvency & Financial Health (Max 20 pts):
       - Debt/Equity < 0.5 or Debt Free: 10 pts, 0.5-1.5: 5 pts
       - ICR > 3.0 or Debt Free: 10 pts, 1.5-3.0: 5 pts

    4. Growth Signals (Max 20 pts):
       - 5-yr Revenue CAGR > 10%: 10 pts, 0-10%: 5 pts
       - 5-yr PAT CAGR > 10%: 10 pts, 0-10%: 5 pts

    Proportionally scales earned points against available max points for missing KPIs.
    """
    earned_pts = 0.0
    max_pts = 0.0

    # 1. Profitability: NPM
    if npm is not None:
        max_pts += 10.0
        if npm > 15.0:
            earned_pts += 10.0
        elif npm >= 5.0:
            earned_pts += 5.0

    # ROE
    if roe is not None:
        max_pts += 10.0
        if roe > 15.0:
            earned_pts += 10.0
        elif roe >= 5.0:
            earned_pts += 5.0

    # ROCE
    if roce is not None:
        max_pts += 10.0
        if roce > 15.0:
            earned_pts += 10.0
        elif roce >= 5.0:
            earned_pts += 5.0

    # 2. Cash Flow Quality
    if cfo_quality_score is not None:
        max_pts += 15.0
        if cfo_quality_score > 1.0:
            earned_pts += 15.0
        elif cfo_quality_score >= 0.5:
            earned_pts += 8.0

    if fcf_conversion is not None:
        max_pts += 15.0
        if fcf_conversion > 80.0:
            earned_pts += 15.0
        elif fcf_conversion >= 40.0:
            earned_pts += 8.0
        elif fcf_conversion > 0.0:
            earned_pts += 4.0

    # 3. Solvency: D/E
    if debt_to_equity is not None or icr_label == "Debt Free":
        max_pts += 10.0
        if icr_label == "Debt Free" or (debt_to_equity is not None and debt_to_equity < 0.5):
            earned_pts += 10.0
        elif debt_to_equity is not None and debt_to_equity <= 1.5:
            earned_pts += 5.0

    # ICR
    if icr is not None or icr_label == "Debt Free":
        max_pts += 10.0
        if icr_label == "Debt Free" or (icr is not None and icr > 3.0):
            earned_pts += 10.0
        elif icr is not None and icr >= 1.5:
            earned_pts += 5.0

    # 4. Growth: 5-yr Revenue CAGR
    if revenue_cagr_5yr is not None:
        max_pts += 10.0
        if revenue_cagr_5yr > 10.0:
            earned_pts += 10.0
        elif revenue_cagr_5yr >= 0.0:
            earned_pts += 5.0

    # 5-yr PAT CAGR
    if pat_cagr_5yr is not None:
        max_pts += 10.0
        if pat_cagr_5yr > 10.0:
            earned_pts += 10.0
        elif pat_cagr_5yr >= 0.0:
            earned_pts += 5.0

    if max_pts == 0.0:
        return None

    score = (earned_pts / max_pts) * 100.0
    return round(score, 2)
