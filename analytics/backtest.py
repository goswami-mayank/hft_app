import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

from .indicators import rsi as _rsi

MIN_BARS = 210


def _sma(values, window):
    return pd.Series(values).rolling(window).mean()


def _rsi_series(values, period=14):
    return _rsi(pd.Series(values), period)


class TrendRsiStrategy(Strategy):
    """Systematic-trading staple: 50/200 SMA crossover confirmed by 14-day RSI extremes."""

    fast_window = 50
    slow_window = 200
    rsi_period = 14

    def init(self):
        self.sma_fast = self.I(_sma, self.data.Close, self.fast_window)
        self.sma_slow = self.I(_sma, self.data.Close, self.slow_window)
        self.rsi = self.I(_rsi_series, self.data.Close, self.rsi_period)

    def next(self):
        if not self.position and (crossover(self.sma_fast, self.sma_slow) or self.rsi[-1] < 30):
            self.buy()
        elif self.position and (crossover(self.sma_slow, self.sma_fast) or self.rsi[-1] > 70):
            self.position.close()


def run_backtest(daily, cash=100_000, commission=0.001):
    """Backtest the trend/RSI strategy on daily bars and benchmark it against buy & hold."""
    data = daily[["Open", "High", "Low", "Close", "Volume"]].dropna()
    if len(data) < MIN_BARS:
        raise ValueError(f"At least {MIN_BARS} daily bars are needed to backtest")

    engine = Backtest(data, TrendRsiStrategy, cash=cash, commission=commission, exclusive_orders=True)
    stats = engine.run()

    equity = stats["_equity_curve"][["Equity"]].rename(columns={"Equity": "Strategy"})
    equity["Buy & Hold"] = data["Close"].reindex(equity.index) / data["Close"].iloc[0] * cash

    summary = {
        "Strategy Return %": float(stats["Return [%]"]),
        "Buy & Hold Return %": float(stats["Buy & Hold Return [%]"]),
        "Sharpe": float(stats["Sharpe Ratio"]),
        "Max Drawdown %": float(stats["Max. Drawdown [%]"]),
        "Win Rate %": float(stats["Win Rate [%]"]),
        "Trades": int(stats["# Trades"]),
    }
    return equity, summary
