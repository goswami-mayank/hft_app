def rsi(close, period=14):
    change = close.diff()
    average_gain = change.clip(lower=0).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    average_loss = -change.clip(upper=0).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    return 100 - 100 / (1 + average_gain / average_loss)


def macd(close):
    line = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    return line, line.ewm(span=9, adjust=False).mean()
