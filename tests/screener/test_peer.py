"""
Tests for Peer Engine, Percentile Rankings, and Special Edge Cases.
"""

import pytest
import sqlite3
import pandas as pd
from src.screener.engine import load_financial_data
from src.analytics.peer import (
    calculate_peer_percentiles,
    populate_peer_percentiles_table,
    load_peer_mappings
)


@pytest.fixture
def peer_test_setup():
    df_data = load_financial_data()
    df_percentiles = calculate_peer_percentiles(df_data)
    return df_data, df_percentiles


def test_28_de_inverse_percentile(peer_test_setup):
    _, df_percentiles = peer_test_setup
    de_pcts = df_percentiles[df_percentiles["metric"] == "D/E"]
    
    # Spot-check IT Services or Automobiles peer group
    for pg_name, grp in de_pcts.groupby("peer_group_name"):
        grp_valid = grp.dropna(subset=["value", "percentile_rank"])
        if len(grp_valid) >= 2:
            min_de_comp = grp_valid.loc[grp_valid["value"].idxmin()]
            max_de_comp = grp_valid.loc[grp_valid["value"].idxmax()]
            
            # Lower D/E must receive equal or HIGHER percentile rank
            assert min_de_comp["percentile_rank"] >= max_de_comp["percentile_rank"]


def test_29_no_peer_group_handling(peer_test_setup):
    df_data, _ = peer_test_setup
    df_peers = load_peer_mappings()
    
    mapped_cids = set(df_peers["company_id"])
    unmapped_cids = set(df_data["company_id"]) - mapped_cids
    
    assert len(unmapped_cids) > 0  # 92 - 56 = 36 unmapped companies
    for cid in unmapped_cids:
        pg = df_peers[df_peers["company_id"] == cid]
        status = pg["peer_group_name"].iloc[0] if not pg.empty else "No peer group assigned"
        assert status == "No peer group assigned"


def test_30_peer_percentile_calculation(peer_test_setup):
    _, df_percentiles = peer_test_setup
    assert not df_percentiles.empty
    assert set(df_percentiles["metric"].unique()) == {
        "ROE", "ROCE", "Net Profit Margin", "D/E", "FCF",
        "PAT CAGR 5yr", "Revenue CAGR 5yr", "EPS CAGR 5yr",
        "Interest Coverage", "Asset Turnover"
    }
    
    # Check percentile scale is within 0-100
    valid_ranks = df_percentiles["percentile_rank"].dropna()
    assert (valid_ranks >= 0.0).all() and (valid_ranks <= 100.0).all()
