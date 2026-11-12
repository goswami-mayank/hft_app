CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { color-scheme: dark; }
.stApp { background: #101612; color: #e7eee8; }
[data-testid="stSidebar"] { background: #151d17; border-right: 1px solid #29342c; width: 310px !important; }
h1, h2, h3, p, label, [data-testid="stMetricLabel"] { font-family: 'Manrope', sans-serif; }
h1 { font-weight: 800; letter-spacing: 0; }
[data-testid="stMetric"] { background: #172019; border: 1px solid #29372d; padding: 14px 16px; border-radius: 6px; }
[data-testid="stMetricValue"] { font-family: 'DM Mono', monospace; }
[data-testid="stBaseButton-primary"] { background: #a7cf8a; border-color: #a7cf8a; color: #101612; }
[data-testid="stBaseButton-primary"]:hover { background: #c4e3a7; border-color: #c4e3a7; color: #101612; }
[data-testid="stAlert"] { background: #1b261e; border: 1px solid #29372d; border-left: 3px solid #a7cf8a; color: #b7c5b9; }
.eyebrow { color: #a7cf8a; font: 500 11px 'DM Mono', monospace; letter-spacing: 1px; }
.market-note { color: #b7c5b9; background: #1b261e; border-left: 3px solid #a7cf8a; padding: 11px 14px; font-size: 13px; }
.signal { display: inline-block; font: 500 12px 'DM Mono', monospace; padding: 5px 9px; border-radius: 4px; }
.signal.buy { color: #c8efac; background: #223b27; }
.signal.sell { color: #ffb6a9; background: #402823; }
.signal.hold { color: #e7d897; background: #39351f; }
.verdict { font: 800 40px 'Manrope', sans-serif; letter-spacing: 0; line-height: 1.1; }
.verdict.buy { color: #a7cf8a; }
.verdict.sell { color: #ed8879; }
.verdict.hold { color: #e2b875; }
.pitch { color: #cbd7cd; font-size: 15px; line-height: 1.6; margin-top: 8px; }
.headline { padding: 6px 0; border-bottom: 1px solid #202a22; font-size: 14px; }
.headline a { color: #e7eee8; text-decoration: none; }
.headline a:hover { color: #a7cf8a; }
</style>
"""

HELP = {
    "scorecard": "One row per company on your dashboard. Every stock runs through the same factor model, "
    "so calls, expected moves and risk can be compared side by side.",
    "verdict": "The gauge adds up independent factor votes (+1 bullish, 0 neutral, -1 bearish): Monte Carlo odds, "
    "trend, momentum, RSI, MACD, Sharpe, and - when available - news sentiment and earnings trend. "
    "A net score of roughly a third of the factor count or more is BUY, the mirror image is SELL, otherwise HOLD. "
    "Confidence is the net score divided by the number of factors.",
    "factors": "The evidence behind the verdict: Monte Carlo odds, long-term trend (50/200-day averages), "
    "12-1 month momentum, RSI mean reversion, MACD crossover, the 1-year Sharpe ratio, and when available, "
    "recent news sentiment and quarterly earnings trend. These are standard building blocks of systematic "
    "(quant) equity strategies, not any single firm's proprietary model.",
    "forecast": "Monte Carlo simulation of 5,000 possible price paths (geometric Brownian motion). "
    "Volatility uses the RiskMetrics EWMA model (lambda 0.94), so recent turbulence weighs more; "
    "drift is the average daily log return of the past year. The dashed line is the median path; "
    "shaded bands contain 50% and 90% of simulated outcomes. Wider bands mean more uncertainty.",
    "trend": "Daily candles for the past year with 50- and 200-day moving averages. Price above a rising "
    "200-day average signals an uptrend. The 50-day crossing above the 200-day (golden cross) is a "
    "classic bullish signal; crossing below (death cross) is bearish.",
    "momentum": "Total return over the last 1, 3, 6 and 12 months. Stocks that outperformed over 3-12 "
    "months tend to keep outperforming in the near term - the momentum premium harvested by systematic funds.",
    "drawdown": "How far the price sits below its previous peak on each day. Deep or long drawdowns show how "
    "painful holding the stock has been and how much downside an investor must tolerate.",
    "distribution": "Histogram of daily returns over the past year. The dotted line is the 1-day 95% "
    "Value-at-Risk: on 19 of 20 days the loss was smaller than this. A long left tail means crash risk.",
    "rsi": "14-day Relative Strength Index. Above 70 the stock is overbought and prone to pull back; "
    "below 30 it is oversold and prone to bounce.",
    "intraday": "One-minute bars streamed through Kafka with Bollinger Bands, MACD and RSI. Use it to time "
    "entries and exits once the daily verdict is set. Requires the collector and storage services.",
    "news": "Recent headlines mentioning the company, pulled from Yahoo Finance and Google News. Each headline "
    "is scored for tone (positive/neutral/negative); the average feeds into the verdict as a news-sentiment vote.",
    "fundamentals": "The company's latest quarterly results and analyst coverage. Revenue growth feeds into the "
    "verdict as an earnings-trend vote; analyst targets and ratings are shown for context.",
    "backtest": "Simulates a simple trend + mean-reversion strategy (50/200-day SMA crossover confirmed by RSI) "
    "over the available daily history, trading costs included, and compares it against simply buying and holding.",
    "macro": "Broad market, policy and geopolitical headlines from Google News, independent of any single "
    "company, for context on what might be moving the wider market.",
}

PITCH = {
    "BUY": "The weight of evidence favours accumulating this stock.",
    "SELL": "The weight of evidence favours reducing or exiting the position.",
    "HOLD": "Signals are mixed; holding and waiting for confirmation is the disciplined call.",
}

CHART_LAYOUT = {
    "template": "plotly_dark",
    "paper_bgcolor": "#151d17",
    "plot_bgcolor": "#151d17",
    "font": {"family": "DM Mono, monospace", "color": "#cbd7cd", "size": 11},
    "margin": {"l": 12, "r": 12, "t": 25, "b": 12},
    "legend": {"orientation": "h", "y": 1.02, "x": 0},
    "hovermode": "x unified",
}
