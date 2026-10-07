"""
Cash Flow KPIs & Capital Allocation Classifier.
Computes Free Cash Flow, CFO Quality Score, CapEx Intensity, FCF Conversion,
and Capital Allocation Pattern Labels.
"""

from typing import Optional, Tuple, List
import numpy as np


def calculate_free_cash_flow(
    operating_activity: Optional[float],
    investing_activity: Optional[float]
) -> Optional[float]:
    """
    Calculate Free Cash Flow (Cr): operating_activity + investing_activity.
    Negative FCF is allowed.
    """
    if operating_activity is None or investing_activity is None:
        return None
    try:
        cfo = float(operating_activity)
        cfi = float(investing_activity)
        if np.isnan(cfo) or np.isnan(cfi):
            return None
        return cfo + cfi
    except (ValueError, TypeError):
        return None


def calculate_cfo_quality_score(
    cfo_series: List[Optional[float]],
    pat_series: List[Optional[float]]
) -> Tuple[Optional[float], Optional[str]]:
    """
    Calculate CFO Quality Score: CFO / PAT averaged over available years (up to 5 years).
    Returns (quality_score, classification):
    - > 1.0: "High Quality"
    - 0.5 to 1.0: "Moderate"
    - < 0.5: "Accrual Risk"
    If PAT is 0 or invalid: returns (None, None).
    """
    if not cfo_series or not pat_series or len(cfo_series) != len(pat_series):
        return None, None

    ratios = []
    for cfo, pat in zip(cfo_series, pat_series):
        if cfo is None or pat is None:
            continue
        try:
            cfo_val = float(cfo)
            pat_val = float(pat)
            if pat_val == 0.0 or np.isnan(cfo_val) or np.isnan(pat_val):
                continue
            ratios.append(cfo_val / pat_val)
        except (ValueError, TypeError):
            continue

    if not ratios:
        return None, None

    avg_score = float(np.mean(ratios))

    if avg_score > 1.0:
        classification = "High Quality"
    elif avg_score >= 0.5:
        classification = "Moderate"
    else:
        classification = "Accrual Risk"

    return avg_score, classification


def calculate_capex_intensity(
    investing_activity: Optional[float],
    sales: Optional[float]
) -> Tuple[Optional[float], Optional[str]]:
    """
    Calculate CapEx Intensity (%): abs(investing_activity) / sales * 100.
    Classification:
    - < 3%: "Asset Light"
    - 3%-8%: "Moderate"
    - > 8%: "Capital Intensive"
    If sales == 0 or missing: returns (None, None).
    """
    if investing_activity is None or sales is None:
        return None, None
    try:
        cfi = float(investing_activity)
        s = float(sales)
        if s <= 0.0 or np.isnan(cfi) or np.isnan(s):
            return None, None

        capex = abs(cfi)
        intensity = (capex / s) * 100.0

        if intensity < 3.0:
            classification = "Asset Light"
        elif intensity <= 8.0:
            classification = "Moderate"
        else:
            classification = "Capital Intensive"

        return intensity, classification
    except (ValueError, TypeError):
        return None, None


def calculate_fcf_conversion(
    fcf: Optional[float],
    operating_profit: Optional[float]
) -> Optional[float]:
    """
    Calculate FCF Conversion Rate (%): FCF / operating_profit * 100.
    If operating_profit == 0 or missing: returns None.
    """
    if fcf is None or operating_profit is None:
        return None
    try:
        fcf_val = float(fcf)
        op_val = float(operating_profit)
        if op_val == 0.0 or np.isnan(fcf_val) or np.isnan(op_val):
            return None
        return (fcf_val / op_val) * 100.0
    except (ValueError, TypeError):
        return None


def classify_capital_allocation(
    cfo: Optional[float],
    cfi: Optional[float],
    cff: Optional[float],
    cfo_pat_ratio: Optional[float] = None
) -> Tuple[str, str, str, str]:
    """
    Classify Capital Allocation Pattern based on signs of CFO, CFI, CFF.
    Returns (cfo_sign, cfi_sign, cff_sign, pattern_label).

    Patterns:
    (+,-,-) with high CFO/PAT (> 1.0) = "Shareholder Returns"
    (+,-,-) otherwise = "Reinvestor"
    (+,+,-) = "Liquidating Assets"
    (-,+,+) = "Distress Signal"
    (-,-,+) = "Growth Funded by Debt"
    (+,+,+) = "Cash Accumulator"
    (-,-,-) = "Pre-Revenue"
    (+,-,+) = "Mixed"
    """
    if cfo is None or cfi is None or cff is None:
        return "N/A", "N/A", "N/A", "Undetermined"

    try:
        cfo_val = float(cfo)
        cfi_val = float(cfi)
        cff_val = float(cff)
        if np.isnan(cfo_val) or np.isnan(cfi_val) or np.isnan(cff_val):
            return "N/A", "N/A", "N/A", "Undetermined"

        cfo_sign = "+" if cfo_val >= 0 else "-"
        cfi_sign = "+" if cfi_val >= 0 else "-"
        cff_sign = "+" if cff_val >= 0 else "-"

        pattern = (cfo_sign, cfi_sign, cff_sign)

        if pattern == ("+", "-", "-"):
            if cfo_pat_ratio is not None and cfo_pat_ratio > 1.0:
                label = "Shareholder Returns"
            else:
                label = "Reinvestor"
        elif pattern == ("+", "+", "-"):
            label = "Liquidating Assets"
        elif pattern == ("-", "+", "+"):
            label = "Distress Signal"
        elif pattern == ("-", "-", "+"):
            label = "Growth Funded by Debt"
        elif pattern == ("+", "+", "+"):
            label = "Cash Accumulator"
        elif pattern == ("-", "-", "-"):
            label = "Pre-Revenue"
        elif pattern == ("+", "-", "+"):
            label = "Mixed"
        else:
            label = "Mixed"

        return cfo_sign, cfi_sign, cff_sign, label

    except (ValueError, TypeError):
        return "N/A", "N/A", "N/A", "Undetermined"
