import numpy as np
import pandas as pd

from .indicators import macd, rsi
from .sentiment import score_headlines

TRADING_DAYS = 252
EWMA_LAMBDA = 0.94  # J.P. Morgan RiskMetrics decay for daily volatility


def _trailing_return(close, days, skip=0):
    if len(close) <= days:
        return float("nan")
    return float(close.iloc[-1 - skip] / close.iloc[-1 - days] - 1)


def forecast_daily(daily, horizon=30, simulations=5000, seed=7, headlines=None, fundamentals=None):
    """Monte Carlo price forecast plus a multi-factor BUY/SELL/HOLD vote on daily bars.

    `headlines` (recent news titles) and `fundamentals` (see app.data.fundamentals) are optional;
    when supplied they add a news-sentiment and an earnings-trend vote to the factor model.
    """
    data = daily.sort_index().copy()
    close = data["Close"].astype(float)
    log_returns = np.log(close).diff().dropna()
    if len(log_returns) < 60:
        raise ValueError("At least 60 daily bars are needed to forecast")

    data["SMA 50"] = close.rolling(50).mean()
    data["SMA 200"] = close.rolling(200).mean()
    data["RSI"] = rsi(close)
    data["MACD"], data["MACD Signal"] = macd(close)
    data["Drawdown"] = close / close.cummax() - 1
    data["Return"] = close.pct_change()

    daily_vol = float(np.sqrt((log_returns**2).ewm(alpha=1 - EWMA_LAMBDA, adjust=False).mean().iloc[-1]))
    daily_drift = float(log_returns.tail(TRADING_DAYS).mean())
    last_price = float(close.iloc[-1])

    rng = np.random.default_rng(seed)
    paths = last_price * np.exp(np.cumsum(rng.normal(daily_drift, daily_vol, (simulations, horizon)), axis=1))
    future_dates = pd.bdate_range(close.index[-1] + pd.Timedelta(days=1), periods=horizon)
    bands = pd.DataFrame(
        np.percentile(paths, [5, 25, 50, 75, 95], axis=0).T,
        index=future_dates,
        columns=["P5", "P25", "P50", "P75", "P95"],
    )
    probability_up = float((paths[:, -1] > last_price).mean())
    median_price = float(bands["P50"].iloc[-1])

    year_returns = data["Return"].tail(TRADING_DAYS).dropna()
    sharpe = float(year_returns.mean() / year_returns.std() * np.sqrt(TRADING_DAYS))
    momentum = {
        "1M": _trailing_return(close, 21),
        "3M": _trailing_return(close, 63),
        "6M": _trailing_return(close, 126),
        "12M": _trailing_return(close, TRADING_DAYS),
    }
    momentum_12_1 = _trailing_return(close, TRADING_DAYS, skip=21)
    latest = data.iloc[-1]

    factors = []

    def vote(name, value, reading):
        factors.append({"Factor": name, "Vote": value, "Reading": reading})

    vote(
        "Monte Carlo odds",
        1 if probability_up >= 0.55 else -1 if probability_up <= 0.45 else 0,
        f"{probability_up:.0%} of {simulations:,} simulated paths end higher in {horizon} sessions",
    )
    if pd.notna(latest["SMA 200"]):
        above = last_price > latest["SMA 200"] and latest["SMA 50"] > latest["SMA 200"]
        below = last_price < latest["SMA 200"] and latest["SMA 50"] < latest["SMA 200"]
        vote(
            "Trend (50/200 SMA)",
            1 if above else -1 if below else 0,
            "Price and 50-day above 200-day" if above else "Price and 50-day below 200-day" if below else "Mixed trend",
        )
    else:
        vote("Trend (50/200 SMA)", 0, "Not enough history for a 200-day average")
    if momentum_12_1 == momentum_12_1:
        vote(
            "Momentum (12-1M)",
            1 if momentum_12_1 > 0.05 else -1 if momentum_12_1 < -0.05 else 0,
            f"{momentum_12_1:+.1%} over 12 months excluding the latest month",
        )
    else:
        vote("Momentum (12-1M)", 0, "Not enough history for 12-month momentum")
    rsi_latest = latest["RSI"]
    vote(
        "Mean reversion (RSI 14)",
        1 if rsi_latest < 30 else -1 if rsi_latest > 70 else 0,
        f"RSI {rsi_latest:.0f}: " + ("oversold" if rsi_latest < 30 else "overbought" if rsi_latest > 70 else "neutral zone"),
    )
    macd_up = latest["MACD"] > latest["MACD Signal"]
    vote("MACD crossover", 1 if macd_up else -1, "MACD above signal line" if macd_up else "MACD below signal line")
    vote(
        "Risk-adjusted return",
        1 if sharpe > 1 else -1 if sharpe < 0 else 0,
        f"1-year Sharpe ratio {sharpe:.2f}",
    )

    sentiment = score_headlines(headlines)
    if sentiment:
        vote(
            "News sentiment",
            1 if sentiment["Compound"] > 0.15 else -1 if sentiment["Compound"] < -0.15 else 0,
            f"{sentiment['Label']} tone across {sentiment['Count']} recent headlines (compound {sentiment['Compound']:+.2f})",
        )

    growth = (fundamentals or {}).get("Revenue Growth QoQ", float("nan"))
    if growth == growth:  # not NaN
        vote(
            "Earnings trend",
            1 if growth > 0.05 else -1 if growth < -0.05 else 0,
            f"Quarterly revenue {'grew' if growth >= 0 else 'fell'} {growth:+.1%} QoQ",
        )

    score = sum(factor["Vote"] for factor in factors)
    threshold = max(2, -(-len(factors) // 3))  # ceil(count / 3), at least 2
    summary = {
        "Signal": "BUY" if score >= threshold else "SELL" if score <= -threshold else "HOLD",
        "Score": score,
        "Confidence": abs(score) / len(factors),
        "Factors": factors,
        "Last Price": last_price,
        "Horizon": horizon,
        "Median Price": median_price,
        "Expected Return": median_price / last_price - 1,
        "Probability Up": probability_up,
        "Range Low": float(bands["P5"].iloc[-1]),
        "Range High": float(bands["P95"].iloc[-1]),
        "Annual Volatility": daily_vol * np.sqrt(TRADING_DAYS),
        "VaR 95": float(-np.percentile(year_returns, 5)),
        "Max Drawdown": float(data["Drawdown"].tail(TRADING_DAYS).min()),
        "Sharpe": sharpe,
        "Momentum": momentum,
    }
    return data, bands, summary
