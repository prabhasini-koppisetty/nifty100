"""
CAGR Engine for multi-year growth rates with complete edge-case classification.
Supports 3-year, 5-year, and 10-year calculations for Revenue, PAT, and EPS.
"""

from typing import Optional, Tuple, List, Dict, Any
import numpy as np


# Edge Case Flag Constants
FLAG_NORMAL = "NORMAL"
FLAG_DECLINE_TO_LOSS = "DECLINE_TO_LOSS"
FLAG_TURNAROUND = "TURNAROUND"
FLAG_BOTH_NEGATIVE = "BOTH_NEGATIVE"
FLAG_ZERO_BASE = "ZERO_BASE"
FLAG_INSUFFICIENT = "INSUFFICIENT"


def calculate_cagr(
    start_val: Optional[float],
    end_val: Optional[float],
    n_years: int
) -> Tuple[Optional[float], str]:
    """
    Calculate Compound Annual Growth Rate (%):
    CAGR = ((end / start) ** (1/n) - 1) * 100

    Handles 6 required edge cases:
    1. Positive -> Positive: calculate normally, flag = NORMAL (or None)
    2. Positive -> Negative: None, flag = DECLINE_TO_LOSS
    3. Negative -> Positive: None, flag = TURNAROUND
    4. Negative -> Negative: None, flag = BOTH_NEGATIVE
    5. Zero base: None, flag = ZERO_BASE
    6. Less than n years / missing values: None, flag = INSUFFICIENT
    """
    if start_val is None or end_val is None or n_years <= 0:
        return None, FLAG_INSUFFICIENT

    try:
        start = float(start_val)
        end = float(end_val)

        if np.isnan(start) or np.isnan(end):
            return None, FLAG_INSUFFICIENT

        # 5. Zero base
        if start == 0.0:
            return None, FLAG_ZERO_BASE

        # 2. Positive -> Negative
        if start > 0.0 and end < 0.0:
            return None, FLAG_DECLINE_TO_LOSS

        # 3. Negative -> Positive
        if start < 0.0 and end > 0.0:
            return None, FLAG_TURNAROUND

        # 4. Negative -> Negative
        if start < 0.0 and end < 0.0:
            return None, FLAG_BOTH_NEGATIVE

        # 1. Positive -> Positive
        if start > 0.0 and end >= 0.0:
            cagr = ((end / start) ** (1.0 / n_years) - 1.0) * 100.0
            return cagr, FLAG_NORMAL

        # Fallback for unexpected edge cases
        return None, FLAG_INSUFFICIENT

    except (ValueError, TypeError, ZeroDivisionError, OverflowError):
        return None, FLAG_INSUFFICIENT


def calculate_series_cagr(
    series_by_year: Dict[str, Optional[float]],
    current_year: str,
    n_years: int
) -> Tuple[Optional[float], str]:
    """
    Helper to calculate CAGR for a metric given a dictionary mapping year ('YYYY-MM') -> value.
    Looks back n_years from current_year based on sorted financial years.
    """
    if not series_by_year or current_year not in series_by_year:
        return None, FLAG_INSUFFICIENT

    sorted_years = sorted(series_by_year.keys())
    try:
        curr_idx = sorted_years.index(current_year)
    except ValueError:
        return None, FLAG_INSUFFICIENT

    start_idx = curr_idx - n_years
    if start_idx < 0:
        return None, FLAG_INSUFFICIENT

    start_year = sorted_years[start_idx]
    start_val = series_by_year[start_year]
    end_val = series_by_year[current_year]

    return calculate_cagr(start_val, end_val, n_years)
