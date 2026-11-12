import pandas as pd

from analytics.forecast import forecast_daily
from analytics.signals import analyze_bars
from sources.prices import read_bars, write_bars


def test_bars_are_upserted_and_isolated_by_ticker(tmp_path):
    timestamp = pd.Timestamp("2026-10-31 09:15:00", tz="UTC")
    first_bar = pd.DataFrame(
        [{"Open": 100, "High": 102, "Low": 99, "Close": 101, "Volume": 10}],
        index=pd.DatetimeIndex([timestamp]),
    )
    updated_bar = first_bar.assign(Close=103)

    write_bars("HCLTECH.NS", first_bar, tmp_path)
    write_bars("HCLTECH.NS", updated_bar, tmp_path)
    write_bars("INFY.NS", first_bar, tmp_path)

    hcltech = read_bars("HCLTECH.NS", tmp_path)
    infy = read_bars("INFY.NS", tmp_path)

    assert len(hcltech) == 1
    assert hcltech.iloc[0]["Close"] == 103
    assert len(infy) == 1
    assert infy.iloc[0]["Close"] == 101


def test_analysis_adds_indicators_and_a_supported_signal():
    index = pd.date_range("2026-10-31 09:15:00", periods=60, freq="min", tz="UTC")
    close = pd.Series([100 + step * 0.1 for step in range(60)], index=index)
    bars = pd.DataFrame(
        {
            "Open": close - 0.05,
            "High": close + 0.1,
            "Low": close - 0.1,
            "Close": close,
            "Volume": 1000,
        },
        index=index,
    )

    analyzed, summary = analyze_bars(bars)

    assert {"MACD", "MACD Signal", "BB Upper", "BB Lower", "RSI"}.issubset(analyzed.columns)
    assert 0 <= analyzed["RSI"].iloc[-1] <= 100
    assert summary["Signal"] in {"BUY", "SELL", "HOLD"}


def test_daily_forecast_bands_and_uptrend_verdict():
    index = pd.bdate_range("2024-11-01", periods=300)
    close = pd.Series([100 * 1.002**step * (1 + 0.01 * (-1) ** step) for step in range(300)], index=index)
    daily = pd.DataFrame(
        {"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close, "Volume": 1000},
        index=index,
    )

    data, bands, summary = forecast_daily(daily, horizon=20)

    assert len(bands) == 20 and bands.index[0] > index[-1]
    assert (bands["P5"] <= bands["P50"]).all() and (bands["P50"] <= bands["P95"]).all()
    assert {"SMA 50", "SMA 200", "Drawdown"}.issubset(data.columns)
    assert len(summary["Factors"]) == 6
    assert summary["Signal"] == "BUY"