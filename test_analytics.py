import pandas as pd

from analytics.backtest import run_backtest
from analytics.forecast import forecast_daily
from analytics.sentiment import score_headlines
from sources.fundamentals import _revenue_growth_qoq


def _synthetic_daily(periods=300, drift=0.002, amplitude=0.01):
    index = pd.bdate_range("2024-11-01", periods=periods)
    close = pd.Series([100 * (1 + drift) ** step * (1 + amplitude * (-1) ** step) for step in range(periods)], index=index)
    return pd.DataFrame(
        {"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 1000},
        index=index,
    )


def test_score_headlines_detects_tone():
    assert score_headlines([]) is None
    bullish = score_headlines(["Company beats estimates and profit soars", "Analysts raise target price"])
    bearish = score_headlines(["Company misses estimates amid fraud probe", "Shares plunge on weak guidance"])
    assert bullish["Label"] == "Positive"
    assert bearish["Label"] == "Negative"


def test_forecast_adds_news_and_earnings_factors():
    daily = _synthetic_daily()
    _, _, base_summary = forecast_daily(daily, horizon=20)
    _, _, extended_summary = forecast_daily(
        daily,
        horizon=20,
        headlines=["Record profit beats estimates", "Strong outlook from management"],
        fundamentals={"Revenue Growth QoQ": 0.08},
    )
    assert len(extended_summary["Factors"]) == len(base_summary["Factors"]) + 2
    factor_names = {factor["Factor"] for factor in extended_summary["Factors"]}
    assert {"News sentiment", "Earnings trend"}.issubset(factor_names)


def test_revenue_growth_qoq_parses_quarterly_financials():
    quarters = pd.DataFrame(
        {
            pd.Timestamp("2025-06-30"): [1100.0],
            pd.Timestamp("2025-03-31"): [1000.0],
        },
        index=["Total Revenue"],
    )
    growth, series = _revenue_growth_qoq(quarters)
    assert round(growth, 6) == 0.1
    assert series.iloc[-1] == 1100.0


def test_backtest_runs_against_buy_and_hold():
    daily = _synthetic_daily(periods=260, drift=0.003, amplitude=0.015)
    equity, summary = run_backtest(daily)

    assert {"Strategy", "Buy & Hold"}.issubset(equity.columns)
    assert "Strategy Return %" in summary and "Sharpe" in summary
