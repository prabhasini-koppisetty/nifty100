"""
Tests for the 6 Screener Presets against real/mock data.
"""

import pytest
import pandas as pd
from src.screener.engine import load_screener_config, load_financial_data, run_preset


@pytest.fixture
def screener_config():
    return load_screener_config()


@pytest.fixture
def real_financial_df():
    return load_financial_data()


def test_18_quality_compounder_preset(real_financial_df, screener_config):
    res = run_preset(real_financial_df, "quality_compounder", screener_config)
    assert isinstance(res, pd.DataFrame)
    for _, row in res.iterrows():
        assert row["return_on_equity_pct"] >= 15.0
        if row["broad_sector"] != "Financials":
            assert row["debt_to_equity"] <= 1.0
        assert row["free_cash_flow_cr"] > 0
        assert row["revenue_cagr_5yr"] >= 10.0


def test_19_value_pick_preset(real_financial_df, screener_config):
    res = run_preset(real_financial_df, "value_pick", screener_config)
    assert isinstance(res, pd.DataFrame)
    for _, row in res.iterrows():
        assert row["pe_ratio"] <= 20.0
        assert row["pb_ratio"] <= 3.0
        if row["broad_sector"] != "Financials":
            assert row["debt_to_equity"] <= 2.0
        assert row["dividend_yield_pct"] >= 1.0


def test_20_growth_accelerator_preset(real_financial_df, screener_config):
    res = run_preset(real_financial_df, "growth_accelerator", screener_config)
    assert isinstance(res, pd.DataFrame)
    for _, row in res.iterrows():
        assert row["pat_cagr_5yr"] >= 20.0
        assert row["revenue_cagr_5yr"] >= 15.0
        if row["broad_sector"] != "Financials":
            assert row["debt_to_equity"] <= 2.0


def test_21_dividend_champion_preset(real_financial_df, screener_config):
    res = run_preset(real_financial_df, "dividend_champion", screener_config)
    assert isinstance(res, pd.DataFrame)
    for _, row in res.iterrows():
        assert row["dividend_yield_pct"] >= 2.0
        if pd.notna(row["dividend_payout_ratio_pct"]):
            assert row["dividend_payout_ratio_pct"] <= 80.0
        assert row["free_cash_flow_cr"] > 0


def test_22_debt_free_blue_chip_preset(real_financial_df, screener_config):
    res = run_preset(real_financial_df, "debt_free_blue_chip", screener_config)
    assert isinstance(res, pd.DataFrame)
    for _, row in res.iterrows():
        if row["broad_sector"] != "Financials":
            assert row["debt_to_equity"] <= 0.0 or row["debt_to_equity"] == 0.0
        assert row["return_on_equity_pct"] >= 12.0
        assert row["sales"] >= 5000.0


def test_23_turnaround_watch_preset(real_financial_df, screener_config):
    res = run_preset(real_financial_df, "turnaround_watch", screener_config)
    assert isinstance(res, pd.DataFrame)
    for _, row in res.iterrows():
        assert row["revenue_cagr_3yr"] >= 10.0
        assert row["free_cash_flow_cr"] > 0
        assert row["de_declining_yoy"] == True
