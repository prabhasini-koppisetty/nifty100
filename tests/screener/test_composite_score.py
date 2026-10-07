"""
Tests for Composite Quality Score, Winsorisation, and Sector-Relative Scoring.
"""

import pytest
import pandas as pd
import numpy as np
from src.screener.engine import calculate_sprint3_composite_score


@pytest.fixture
def sample_score_df():
    return pd.DataFrame([
        {
            "company_id": "C1",
            "broad_sector": "IT",
            "return_on_equity_pct": 25.0,
            "return_on_capital_employed_pct": 30.0,
            "net_profit_margin_pct": 20.0,
            "free_cash_flow_cr": 500.0,
            "cfo_quality_score": 1.2,
            "revenue_cagr_5yr": 15.0,
            "pat_cagr_5yr": 18.0,
            "debt_to_equity": 0.1,
            "interest_coverage": 10.0
        },
        {
            "company_id": "C2",
            "broad_sector": "IT",
            "return_on_equity_pct": 10.0,
            "return_on_capital_employed_pct": 12.0,
            "net_profit_margin_pct": 8.0,
            "free_cash_flow_cr": -50.0,
            "cfo_quality_score": 0.4,
            "revenue_cagr_5yr": 5.0,
            "pat_cagr_5yr": 4.0,
            "debt_to_equity": 1.5,
            "interest_coverage": 2.0
        },
        {
            "company_id": "C3",
            "broad_sector": "Auto",
            "return_on_equity_pct": 18.0,
            "return_on_capital_employed_pct": 20.0,
            "net_profit_margin_pct": 12.0,
            "free_cash_flow_cr": 200.0,
            "cfo_quality_score": 0.9,
            "revenue_cagr_5yr": 10.0,
            "pat_cagr_5yr": 12.0,
            "debt_to_equity": 0.3,
            "interest_coverage": 6.0
        }
    ])


def test_25_composite_score_calculation(sample_score_df):
    res = calculate_sprint3_composite_score(sample_score_df)
    assert "composite_quality_score" in res.columns
    # C1 is highest performing, C2 is lowest
    c1_score = res[res["company_id"] == "C1"]["composite_quality_score"].values[0]
    c2_score = res[res["company_id"] == "C2"]["composite_quality_score"].values[0]
    assert c1_score > c2_score
    assert 0.0 <= c1_score <= 100.0
    assert 0.0 <= c2_score <= 100.0


def test_26_winsorisation(sample_score_df):
    # Add outlier company
    outlier_df = pd.concat([
        sample_score_df,
        pd.DataFrame([{
            "company_id": "OUTLIER",
            "broad_sector": "IT",
            "return_on_equity_pct": 500.0,  # Extreme outlier
            "return_on_capital_employed_pct": 600.0,
            "net_profit_margin_pct": 90.0,
            "free_cash_flow_cr": 10000.0,
            "cfo_quality_score": 5.0,
            "revenue_cagr_5yr": 100.0,
            "pat_cagr_5yr": 120.0,
            "debt_to_equity": 0.0,
            "interest_coverage": 100.0
        }])
    ], ignore_index=True)

    res = calculate_sprint3_composite_score(outlier_df)
    score_outlier = res[res["company_id"] == "OUTLIER"]["composite_quality_score"].values[0]
    # Winsorisation should cap normalized values so outlier doesn't break scale
    assert score_outlier <= 100.0


def test_27_sector_relative_score(sample_score_df):
    res = calculate_sprint3_composite_score(sample_score_df)
    assert "sector_composite_quality_score" in res.columns
    # Sector relative score should be calculated per broad_sector
    it_scores = res[res["broad_sector"] == "IT"]["sector_composite_quality_score"]
    assert len(it_scores) == 2
    assert not it_scores.isna().any()
