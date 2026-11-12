import re
import sqlite3
from pathlib import Path

import pandas as pd
import yfinance as yf

BAR_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def download_bars(ticker, period="7d", interval="1m"):
    """Fetch OHLCV bars from Yahoo Finance for any period/interval (intraday or daily)."""
    bars = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if bars.empty:
        return bars
    if isinstance(bars.columns, pd.MultiIndex):
        if ticker in bars.columns.get_level_values(0):
            bars = bars[ticker]
        else:
            bars.columns = bars.columns.get_level_values(0)
    bars.columns = [str(column).title() for column in bars.columns]
    return bars.dropna(subset=["Close"])


def serialize_bars(ticker, bars):
    items = []
    for timestamp, row in bars.iterrows():
        timestamp = pd.Timestamp(timestamp)
        timestamp = timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")
        item = {"timestamp": timestamp.isoformat()}
        item.update(
            {
                column: None if pd.isna(row[column]) else float(row[column])
                for column in BAR_COLUMNS
            }
        )
        items.append(item)
    return {"ticker": ticker, "bars": items}


def search_companies(query):
    query = query.strip()
    matches = []
    if re.fullmatch(r"[A-Za-z0-9._^=-]+", query):
        direct = query.upper()
        if not direct.endswith((".NS", ".BO")) and not direct.startswith("^"):
            direct += ".NS"
        matches.append({"symbol": direct, "name": f"{direct} · direct ticker"})

    try:
        for quote in yf.Search(query, max_results=10).quotes:
            symbol = str(quote.get("symbol", "")).upper()
            if symbol.endswith((".NS", ".BO")):
                matches.append(
                    {
                        "symbol": symbol,
                        "name": quote.get("shortname") or quote.get("longname") or symbol,
                    }
                )
    except Exception:
        pass

    unique = {}
    for match in matches:
        unique.setdefault(match["symbol"], match)
    return list(unique.values())


def _database_path(ticker, data_dir):
    safe_ticker = re.sub(r"[^A-Z0-9_-]", "_", ticker.upper())
    if not safe_ticker:
        raise ValueError("Ticker must contain at least one letter or number")
    return Path(data_dir) / f"{safe_ticker}.sqlite3"


def write_bars(ticker, bars, data_dir="data"):
    if bars.empty:
        return

    missing = set(BAR_COLUMNS).difference(bars.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {', '.join(sorted(missing))}")

    path = _database_path(ticker, data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for timestamp, bar in bars[BAR_COLUMNS].iterrows():
        timestamp = pd.Timestamp(timestamp)
        timestamp = timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")
        values = [None if pd.isna(value) else float(value) for value in bar]
        rows.append((timestamp.isoformat(), *values))

    with sqlite3.connect(path, timeout=30) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS bars (
                timestamp TEXT PRIMARY KEY,
                open REAL, high REAL, low REAL, close REAL, volume REAL
            )"""
        )
        connection.executemany(
            "INSERT OR REPLACE INTO bars VALUES (?, ?, ?, ?, ?, ?)", rows
        )


def read_bars(ticker, data_dir="data"):
    path = _database_path(ticker, data_dir)
    if not path.exists():
        return pd.DataFrame(columns=BAR_COLUMNS, index=pd.DatetimeIndex([], tz="UTC"))

    with sqlite3.connect(path, timeout=30) as connection:
        bars = pd.read_sql_query("SELECT * FROM bars ORDER BY timestamp", connection)

    bars = bars.rename(columns=str.title).set_index("Timestamp")
    bars.index = pd.to_datetime(bars.index, utc=True)
    return bars[BAR_COLUMNS]
