import math

import yfinance as yf


def _revenue_growth_qoq(quarterly_financials):
    try:
        revenue = quarterly_financials.loc["Total Revenue"].dropna().sort_index(ascending=False)
        if len(revenue) < 2:
            return float("nan"), None
        growth = float(revenue.iloc[0] / revenue.iloc[1] - 1)
        return growth, revenue.sort_index()
    except Exception:
        return float("nan"), None


def fetch_fundamentals(ticker):
    """Best-effort quarterly results and analyst coverage; Yahoo Finance's schema varies across tickers."""
    handle = yf.Ticker(ticker)
    growth, revenue_series = _revenue_growth_qoq(handle.quarterly_financials)

    info = {}
    try:
        info = handle.info or {}
    except Exception:
        pass

    target = info.get("targetMeanPrice")
    return {
        "Revenue Growth QoQ": growth,
        "Quarterly Revenue": revenue_series,
        "Analyst Target": float(target) if isinstance(target, (int, float)) and not math.isnan(target) else None,
        "Analyst Recommendation": info.get("recommendationKey"),
        "Analyst Count": info.get("numberOfAnalystOpinions"),
    }
