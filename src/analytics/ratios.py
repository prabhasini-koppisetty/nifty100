"""
Profitability, Leverage, and Efficiency Ratio calculations for Nifty 100 companies.
Handles zero denominators, negative equity, sector carve-outs, and edge cases.
"""

import logging
from typing import Optional, Union, Tuple

# Setup logger for ratio engine
logger = logging.getLogger(__name__)


def calculate_net_profit_margin(
    net_profit: Optional[float],
    sales: Optional[float]
) -> Optional[float]:
    """
    Calculate Net Profit Margin (%): (net_profit / sales) * 100.
    Returns None if sales is None, NaN, or zero.
    """
    if sales is None or net_profit is None:
        return None
    try:
        sales_val = float(sales)
        net_profit_val = float(net_profit)
        if sales_val == 0.0:
            return None
        return (net_profit_val / sales_val) * 100.0
    except (ValueError, TypeError):
        return None


def calculate_operating_profit_margin(
    operating_profit: Optional[float],
    sales: Optional[float],
    source_opm: Optional[float] = None,
    company_id: Optional[str] = None,
    year: Optional[str] = None
) -> Optional[float]:
    """
    Calculate Operating Profit Margin (%): (operating_profit / sales) * 100.
    Cross-checks against source OPM if provided.
    Logs mismatch if absolute difference > 1%, but retains calculated value.
    """
    if sales is None or operating_profit is None:
        return None
    try:
        sales_val = float(sales)
        op_val = float(operating_profit)
        if sales_val == 0.0:
            return None
        computed_opm = (op_val / sales_val) * 100.0

        if source_opm is not None:
            try:
                src_opm_val = float(source_opm)
                diff = abs(computed_opm - src_opm_val)
                if diff > 1.0:
                    logger.warning(
                        f"OPM mismatch for {company_id or 'UNKNOWN'} ({year or 'N/A'}): "
                        f"Computed={computed_opm:.2f}%, Source={src_opm_val:.2f}%, Diff={diff:.2f}%"
                    )
            except (ValueError, TypeError):
                pass

        return computed_opm
    except (ValueError, TypeError):
        return None


def calculate_return_on_equity(
    net_profit: Optional[float],
    equity_capital: Optional[float],
    reserves: Optional[float]
) -> Optional[float]:
    """
    Calculate Return on Equity (%): net_profit / (equity_capital + reserves) * 100.
    Returns None if equity + reserves <= 0 or inputs are missing.
    """
    if net_profit is None or equity_capital is None or reserves is None:
        return None
    try:
        np_val = float(net_profit)
        eq_val = float(equity_capital)
        res_val = float(reserves)
        total_equity = eq_val + res_val
        if total_equity <= 0.0:
            return None
        return (np_val / total_equity) * 100.0
    except (ValueError, TypeError):
        return None


def calculate_return_on_capital_employed(
    ebit: Optional[float],
    equity_capital: Optional[float],
    reserves: Optional[float],
    borrowings: Optional[float],
    is_financial: bool = False
) -> Optional[float]:
    """
    Calculate Return on Capital Employed (%): EBIT / (equity + reserves + borrowings) * 100.
    EBIT = profit_before_tax + interest (or operating_profit + other_income - depreciation).
    Returns None if capital employed <= 0 or inputs missing.
    For Financials broad_sector, high leverage is normal.
    """
    if ebit is None or equity_capital is None or reserves is None:
        return None
    try:
        ebit_val = float(ebit)
        eq_val = float(equity_capital)
        res_val = float(reserves)
        borr_val = float(borrowings) if borrowings is not None else 0.0
        capital_employed = eq_val + res_val + borr_val
        if capital_employed <= 0.0:
            return None
        return (ebit_val / capital_employed) * 100.0
    except (ValueError, TypeError):
        return None


def calculate_return_on_assets(
    net_profit: Optional[float],
    total_assets: Optional[float]
) -> Optional[float]:
    """
    Calculate Return on Assets (%): net_profit / total_assets * 100.
    Returns None if total_assets <= 0 or missing.
    """
    if net_profit is None or total_assets is None:
        return None
    try:
        np_val = float(net_profit)
        assets_val = float(total_assets)
        if assets_val <= 0.0:
            return None
        return (np_val / assets_val) * 100.0
    except (ValueError, TypeError):
        return None


def calculate_debt_to_equity(
    borrowings: Optional[float],
    equity_capital: Optional[float],
    reserves: Optional[float]
) -> Optional[float]:
    """
    Calculate Debt-to-Equity Ratio: borrowings / (equity_capital + reserves).
    - If borrowings == 0, returns 0.0 (NOT None).
    - If equity + reserves <= 0, returns None.
    """
    if equity_capital is None or reserves is None:
        return None
    try:
        borr_val = float(borrowings) if borrowings is not None else 0.0
        eq_val = float(equity_capital)
        res_val = float(reserves)
        total_equity = eq_val + res_val

        if total_equity <= 0.0:
            return None
        if borr_val == 0.0:
            return 0.0
        return borr_val / total_equity
    except (ValueError, TypeError):
        return None


def calculate_high_leverage_flag(
    debt_to_equity: Optional[float],
    is_financial: bool = False
) -> bool:
    """
    Check for High Leverage Flag:
    Returns True if D/E > 5 AND company is NOT in Financials broad_sector.
    Otherwise False.
    """
    if debt_to_equity is None:
        return False
    if is_financial:
        return False
    return debt_to_equity > 5.0


def calculate_interest_coverage(
    operating_profit: Optional[float],
    other_income: Optional[float],
    interest: Optional[float]
) -> Optional[float]:
    """
    Calculate Interest Coverage Ratio (ICR): (operating_profit + other_income) / interest.
    If interest is 0 or None/NaN, returns None.
    """
    if interest is None:
        return None
    try:
        int_val = float(interest)
        if int_val <= 0.0:
            return None
        op_val = float(operating_profit) if operating_profit is not None else 0.0
        oth_val = float(other_income) if other_income is not None else 0.0
        ebitda_like = op_val + oth_val
        return ebitda_like / int_val
    except (ValueError, TypeError):
        return None


def calculate_icr_label(
    interest_coverage: Optional[float],
    interest: Optional[float] = None,
    borrowings: Optional[float] = None
) -> Optional[str]:
    """
    Determine ICR Label:
    If ICR is None and (interest == 0 or borrowings == 0 or interest is None):
    returns 'Debt Free'.
    Otherwise None.
    """
    try:
        int_val = float(interest) if interest is not None else 0.0
        borr_val = float(borrowings) if borrowings is not None else 0.0
        if interest_coverage is None:
            if int_val == 0.0 or borr_val == 0.0:
                return "Debt Free"
        return None
    except (ValueError, TypeError):
        return "Debt Free"


def calculate_icr_warning_flag(
    interest_coverage: Optional[float]
) -> bool:
    """
    ICR Warning Flag: True if ICR < 1.5 (and ICR is not None). Otherwise False.
    """
    if interest_coverage is None:
        return False
    return interest_coverage < 1.5


def calculate_net_debt(
    borrowings: Optional[float],
    investments: Optional[float]
) -> Optional[float]:
    """
    Calculate Net Debt (Cr): borrowings - investments.
    Uses investments as the liquid asset proxy.
    """
    try:
        borr_val = float(borrowings) if borrowings is not None else 0.0
        inv_val = float(investments) if investments is not None else 0.0
        return borr_val - inv_val
    except (ValueError, TypeError):
        return None


def calculate_asset_turnover(
    sales: Optional[float],
    total_assets: Optional[float]
) -> Optional[float]:
    """
    Calculate Asset Turnover: sales / total_assets.
    Returns None if total_assets is zero, negative, or missing.
    """
    if sales is None or total_assets is None:
        return None
    try:
        sales_val = float(sales)
        assets_val = float(total_assets)
        if assets_val <= 0.0:
            return None
        return sales_val / assets_val
    except (ValueError, TypeError):
        return None
