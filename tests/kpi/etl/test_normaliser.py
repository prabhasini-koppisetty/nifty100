import pandas as pd
import pytest
from src.etl.normaliser import normalize_ticker, normalize_year


# =====================================================================
# 20 UNIT TESTS FOR normalize_year()
# =====================================================================

def test_normalize_year_mar_2024():
    assert normalize_year("Mar 2024") == "2024-03"


def test_normalize_year_mar_dash_24():
    assert normalize_year("Mar-24") == "2024-03"


def test_normalize_year_mar_2023_15():
    assert normalize_year("Mar 2023 15") == "2023-03"


def test_normalize_year_mar_2016_9m():
    assert normalize_year("Mar 2016 9m") == "2016-03"


def test_normalize_year_jan_2020():
    assert normalize_year("Jan 2020") == "2020-01"


def test_normalize_year_feb_2021():
    assert normalize_year("Feb 2021") == "2021-02"


def test_normalize_year_apr_dash_22():
    assert normalize_year("Apr-22") == "2022-04"


def test_normalize_year_may_2018():
    assert normalize_year("May 2018") == "2018-05"


def test_normalize_year_jun_dash_19():
    assert normalize_year("Jun-19") == "2019-06"


def test_normalize_year_jul_2015():
    assert normalize_year("Jul 2015") == "2015-07"


def test_normalize_year_aug_dash_25():
    assert normalize_year("Aug-25") == "2025-08"


def test_normalize_year_sep_2023():
    assert normalize_year("Sep 2023") == "2023-09"


def test_normalize_year_oct_dash_17():
    assert normalize_year("Oct-17") == "2017-10"


def test_normalize_year_nov_2012():
    assert normalize_year("Nov 2012") == "2012-11"


def test_normalize_year_dec_2014():
    assert normalize_year("Dec 2014") == "2014-12"


def test_normalize_year_ttm():
    assert normalize_year("TTM") == "TTM"


def test_normalize_year_already_normalized():
    assert normalize_year("2024-03") == "2024-03"


def test_normalize_year_none():
    assert normalize_year(None) is None


def test_normalize_year_empty_string():
    assert normalize_year("") is None


def test_normalize_year_invalid_string():
    assert normalize_year("InvalidYear") is None


# =====================================================================
# 15 UNIT TESTS FOR normalize_ticker()
# =====================================================================

def test_normalize_ticker_lowercase():
    assert normalize_ticker("hdfcbank") == "HDFCBANK"


def test_normalize_ticker_with_spaces():
    assert normalize_ticker(" SBILIFE ") == "SBILIFE"


def test_normalize_ticker_tcs():
    assert normalize_ticker("tcs") == "TCS"


def test_normalize_ticker_wipro():
    assert normalize_ticker("wipro") == "WIPRO"


def test_normalize_ticker_infy():
    assert normalize_ticker("infy") == "INFY"


def test_normalize_ticker_ongc():
    assert normalize_ticker("ongc") == "ONGC"


def test_normalize_ticker_heromotoco():
    assert normalize_ticker("heromotoco") == "HEROMOTOCO"


def test_normalize_ticker_icicigi():
    assert normalize_ticker("icicigi") == "ICICIGI"


def test_normalize_ticker_lici():
    assert normalize_ticker("lici") == "LICI"


def test_normalize_ticker_reliance_spaces():
    assert normalize_ticker(" reliance ") == "RELIANCE"


def test_normalize_ticker_none():
    assert normalize_ticker(None) is None


def test_normalize_ticker_pandas_na():
    assert normalize_ticker(pd.NA) is None


def test_normalize_ticker_empty_string():
    assert normalize_ticker("") is None


def test_normalize_ticker_spaces_only():
    assert normalize_ticker("   ") is None


def test_normalize_ticker_numeric_id():
    assert normalize_ticker("12345") == "12345"
