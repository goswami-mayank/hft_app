import io
import requests
import yfinance as yf
import pandas as pd

# -----------------------------------
# 1. Get list of all NSE-listed companies
# -----------------------------------

NSE_LIST_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
OUTPUT_CSV = "nse_trading_signals.csv"
BATCH_SIZE = 100

# NSE rejects requests without a browser User-Agent
resp = requests.get(NSE_LIST_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
resp.raise_for_status()
companies = pd.read_csv(io.StringIO(resp.text))
companies.columns = companies.columns.str.strip()
companies = companies[companies["SERIES"].str.strip() == "EQ"]

name_by_ticker = {
    f"{sym.strip()}.NS": name
    for sym, name in zip(companies["SYMBOL"], companies["NAME OF COMPANY"])
}
tickers = list(name_by_ticker)
print(f"Scanning {len(tickers)} NSE companies...")

# -----------------------------------
# 2. Markov chain signal logic
# -----------------------------------

THRESHOLD = 0.0002
MIN_EDGE = 0.0005
states = ["UP", "DOWN", "SIDEWAYS"]


def classify_market_state(ret):
    if ret > THRESHOLD:
        return "UP"
    elif ret < -THRESHOLD:
        return "DOWN"
    return "SIDEWAYS"


def compute_signal(close):
    returns = close.dropna().pct_change().dropna()
    if len(returns) < 30:
        return None

    state_series = returns.apply(classify_market_state)

    transition_counts = pd.DataFrame(1.0, index=states, columns=states)
    for previous, current in zip(state_series.iloc[:-1], state_series.iloc[1:]):
        transition_counts.loc[previous, current] += 1
    transition_matrix = transition_counts.div(transition_counts.sum(axis=1), axis=0)

    state_returns = returns.groupby(state_series).mean().reindex(states, fill_value=0.0)

    last_state = state_series.iloc[-1]
    expected_return = float((transition_matrix.loc[last_state] * state_returns).sum())
    last_price = float(close.dropna().iloc[-1])

    if expected_return > MIN_EDGE:
        signal = "BUY"
    elif expected_return < -MIN_EDGE:
        signal = "SELL"
    else:
        signal = "HOLD"

    return {
        "Last Price": round(last_price, 2),
        "Last State": last_state,
        "Expected Return %": round(expected_return * 100, 5),
        "Forecast Price": round(last_price * (1 + expected_return), 2),
        "Signal": signal,
    }

# -----------------------------------
# 3. Download data in batches and compute signals
# -----------------------------------

results = []
for i in range(0, len(tickers), BATCH_SIZE):
    batch = tickers[i:i + BATCH_SIZE]
    df = yf.download(
        batch,
        period="7d",
        interval="1m",
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=True,
    )
    if df.empty:
        continue
    available = set(df.columns.get_level_values(0))
    for t in batch:
        if t not in available:
            continue
        res = compute_signal(df[t]["Close"])
        if res:
            results.append({"Ticker": t, "Company": name_by_ticker[t], **res})
    print(f"Processed {min(i + BATCH_SIZE, len(tickers))}/{len(tickers)}")

# -----------------------------------
# 4. Save to CSV
# -----------------------------------

signals_df = (
    pd.DataFrame(results)
    .sort_values(["Signal", "Expected Return %"], ascending=[True, False])
    .reset_index(drop=True)
)
signals_df.to_csv(OUTPUT_CSV, index=False)

print(f"\nSaved {len(signals_df)} companies to {OUTPUT_CSV}")
print(signals_df["Signal"].value_counts())