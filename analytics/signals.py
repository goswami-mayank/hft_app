import pandas as pd

from .indicators import macd, rsi

STATES = ["UP", "DOWN", "SIDEWAYS"]
STATE_THRESHOLD = 0.0002
MIN_EDGE = 0.0005


def analyze_bars(bars):
    """Intraday Markov-chain next-bar forecast plus MACD/RSI/Bollinger confirmation."""
    data = bars.sort_index().copy()
    close = data["Close"].astype(float)
    data["Return"] = close.pct_change()
    data["State"] = data["Return"].map(
        lambda value: (
            "UP" if value > STATE_THRESHOLD
            else "DOWN" if value < -STATE_THRESHOLD
            else "SIDEWAYS"
        )
        if pd.notna(value)
        else None
    )

    data["MACD"], data["MACD Signal"] = macd(close)
    middle = close.rolling(20).mean()
    deviation = close.rolling(20).std()
    data["BB Upper"] = middle + 2 * deviation
    data["BB Lower"] = middle - 2 * deviation
    data["RSI"] = rsi(close)

    returns = data["Return"].dropna()
    observed_states = data["State"].dropna()
    transition_counts = pd.DataFrame(1.0, index=STATES, columns=STATES)
    for previous, current in zip(observed_states.iloc[:-1], observed_states.iloc[1:]):
        transition_counts.loc[previous, current] += 1
    transition_matrix = transition_counts.div(transition_counts.sum(axis=1), axis=0)
    state_returns = returns.groupby(observed_states).mean().reindex(STATES, fill_value=0.0)

    last_state = observed_states.iloc[-1] if not observed_states.empty else "SIDEWAYS"
    expected_return = float(
        (transition_matrix.loc[last_state] * state_returns).sum()
    )
    latest = data.iloc[-1]
    score = 0
    score += 1 if expected_return > MIN_EDGE else -1 if expected_return < -MIN_EDGE else 0

    if pd.notna(latest["MACD Signal"]):
        score += 1 if latest["MACD"] > latest["MACD Signal"] else -1
    if pd.notna(latest["RSI"]):
        score += 1 if latest["RSI"] < 30 else -1 if latest["RSI"] > 70 else 0
    if pd.notna(latest["BB Lower"]) and latest["Close"] < latest["BB Lower"]:
        score += 1
    elif pd.notna(latest["BB Upper"]) and latest["Close"] > latest["BB Upper"]:
        score -= 1

    signal = "BUY" if score >= 2 else "SELL" if score <= -2 else "HOLD"
    last_price = float(close.iloc[-1])
    summary = {
        "Signal": signal,
        "Last State": last_state,
        "Last Price": last_price,
        "Expected Return %": expected_return * 100,
        "Forecast Price": last_price * (1 + expected_return),
        "RSI": latest["RSI"],
        "MACD": latest["MACD"],
        "MACD Signal": latest["MACD Signal"],
        "Score": score,
    }
    return data, summary
