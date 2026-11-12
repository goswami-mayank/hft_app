import json

import pandas as pd
import streamlit as st
from confluent_kafka import Producer

from analytics.backtest import run_backtest
from analytics.forecast import forecast_daily
from analytics.sentiment import score_headlines
from analytics.signals import analyze_bars
from config import DATA_DIR, KAFKA_BOOTSTRAP_SERVERS, MACRO_TOPICS, SUBSCRIPTION_TOPIC
from sources.fundamentals import fetch_fundamentals
from sources.news import fetch_company_news, fetch_macro_news
from sources.prices import download_bars, read_bars, search_companies
from ui.charts import (
    backtest_equity_chart,
    drawdown_chart,
    distribution_chart,
    forecast_chart,
    gauge_chart,
    intraday_chart,
    momentum_chart,
    revenue_chart,
    rsi_chart,
    trend_chart,
)
from ui.theme import CHART_LAYOUT, CSS, HELP, PITCH


@st.cache_resource
def get_kafka_producer():
    return Producer({"bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS})


@st.cache_data(ttl=300, show_spinner=False)
def cached_search(query):
    return search_companies(query)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_company_news(ticker, name):
    return fetch_company_news(ticker, name)


@st.cache_data(ttl=21600, show_spinner=False)
def cached_fundamentals(ticker):
    return fetch_fundamentals(ticker)


@st.cache_data(ttl=1800, show_spinner=False)
def cached_macro_news():
    return fetch_macro_news(MACRO_TOPICS)


@st.cache_data(ttl=3600, show_spinner=False)
def company_forecast(ticker, name, horizon):
    daily = download_bars(ticker, period="2y", interval="1d")
    if daily.empty:
        raise ValueError("Yahoo Finance returned no daily history")
    headlines = [item["title"] for item in cached_company_news(ticker, name)]
    fundamentals = cached_fundamentals(ticker)
    return forecast_daily(daily, horizon, headlines=headlines, fundamentals=fundamentals)


def show(fig, key, height=340):
    fig.update_layout(**CHART_LAYOUT, height=height)
    fig.update_xaxes(showgrid=True, gridcolor="#27332a")
    fig.update_yaxes(showgrid=True, gridcolor="#27332a")
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False}, key=key)


def render_scorecard(watchlist, horizon):
    rows = []
    for ticker, name in watchlist.items():
        try:
            _, _, summary = company_forecast(ticker, name, horizon)
        except Exception:
            continue
        rows.append(
            {
                "Company": name,
                "Ticker": ticker,
                "Call": summary["Signal"],
                "Score": summary["Score"],
                "Last": summary["Last Price"],
                "Target": summary["Median Price"],
                "Expected move": summary["Expected Return"] * 100,
                "Odds of gain": summary["Probability Up"] * 100,
                "Volatility": summary["Annual Volatility"] * 100,
            }
        )
    if not rows:
        return
    st.subheader("Watchlist scorecard", help=HELP["scorecard"])
    percent = st.column_config.NumberColumn(format="%.1f%%")
    rupees = st.column_config.NumberColumn(format="₹%.2f")
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Last": rupees,
            "Target": rupees,
            "Expected move": percent,
            "Odds of gain": percent,
            "Volatility": percent,
        },
    )


def _render_overview(ticker, horizon, data, bands, summary):
    signal = summary["Signal"]
    votes = [factor["Vote"] for factor in summary["Factors"]]
    target_date = bands.index[-1].strftime("%d %b %Y")

    st.subheader("Verdict", help=HELP["verdict"])
    left, right = st.columns([1, 1.6])
    with left:
        show(gauge_chart(summary["Score"], len(votes)), f"{ticker}-gauge", height=230)
    with right:
        st.markdown(
            f'<div class="verdict {signal.lower()}">{signal}</div>'
            f'<div class="eyebrow">CONFIDENCE {summary["Confidence"]:.0%} · {summary["Horizon"]}-SESSION VIEW</div>'
            f'<div class="pitch">{PITCH[signal]} {votes.count(1)} bullish, {votes.count(-1)} bearish and '
            f"{votes.count(0)} neutral factors. The Monte Carlo median points to "
            f'<b>₹{summary["Median Price"]:,.2f}</b> by {target_date} ({summary["Expected Return"]:+.1%}), '
            f'with a 90% range of ₹{summary["Range Low"]:,.2f} - ₹{summary["Range High"]:,.2f}.</div>',
            unsafe_allow_html=True,
        )

    st.subheader("Why this call", help=HELP["factors"])
    factors = pd.DataFrame(summary["Factors"])
    factors["Vote"] = factors["Vote"].map({1: "Bullish", 0: "Neutral", -1: "Bearish"})
    st.dataframe(factors, hide_index=True, use_container_width=True)

    metrics = st.columns(6)
    metrics[0].metric("LAST CLOSE", f"₹{summary['Last Price']:,.2f}", help="Most recent daily closing price.")
    metrics[1].metric(
        f"{horizon}-SESSION TARGET",
        f"₹{summary['Median Price']:,.2f}",
        f"{summary['Expected Return']:+.1%}",
        help="Median simulated price at the end of the forecast horizon; the delta is the expected move.",
    )
    metrics[2].metric(
        "ODDS OF GAIN",
        f"{summary['Probability Up']:.0%}",
        help="Share of simulated paths that finish above today's price.",
    )
    metrics[3].metric(
        "VOLATILITY · ANN.",
        f"{summary['Annual Volatility']:.1%}",
        help="EWMA volatility scaled to one year. Indian large caps typically sit around 20-30%.",
    )
    metrics[4].metric(
        "1-DAY VaR 95%",
        f"{summary['VaR 95']:.2%}",
        help="Historical Value-at-Risk: on 95% of days over the past year the loss was smaller than this.",
    )
    metrics[5].metric(
        "SHARPE · 1Y",
        f"{summary['Sharpe']:.2f}",
        help="Annualised return per unit of risk (risk-free rate ignored). Above 1 is strong; below 0 means losses.",
    )

    st.subheader("Price forecast", help=HELP["forecast"])
    show(forecast_chart(data, bands), f"{ticker}-forecast", height=420)

    st.subheader("Trend · 50/200-day averages", help=HELP["trend"])
    show(trend_chart(data), f"{ticker}-trend", height=420)

    left, right = st.columns(2)
    with left:
        st.subheader("Momentum", help=HELP["momentum"])
        show(momentum_chart(summary["Momentum"]), f"{ticker}-momentum")
    with right:
        st.subheader(f"Drawdown · max {summary['Max Drawdown']:.1%}", help=HELP["drawdown"])
        show(drawdown_chart(data), f"{ticker}-drawdown")

    left, right = st.columns(2)
    with left:
        st.subheader("Daily return distribution", help=HELP["distribution"])
        show(distribution_chart(data, summary["VaR 95"]), f"{ticker}-distribution")
    with right:
        st.subheader("RSI · 14 day", help=HELP["rsi"])
        show(rsi_chart(data), f"{ticker}-rsi")


def _headline_html(item, badge_class=None):
    badge = f'<span class="signal {badge_class}">{item.get("Label", "")}</span> ' if badge_class else ""
    return (
        f'<div class="headline">{badge}<a href="{item.get("link", "")}" target="_blank">{item.get("title", "")}</a> '
        f'<span class="eyebrow">{item.get("source", "")} {item.get("published", "")}</span></div>'
    )


def _render_news(ticker, name):
    st.subheader("Recent headlines", help=HELP["news"])
    articles = cached_company_news(ticker, name)
    if not articles:
        st.info("No recent headlines found for this company.")
        return

    scored = []
    for item in articles:
        sentiment = score_headlines([item["title"]]) or {"Label": "Neutral"}
        scored.append({**item, **sentiment})

    positive = sum(1 for item in scored if item["Label"] == "Positive")
    negative = sum(1 for item in scored if item["Label"] == "Negative")
    cols = st.columns(3)
    cols[0].metric("POSITIVE", positive)
    cols[1].metric("NEUTRAL", len(scored) - positive - negative)
    cols[2].metric("NEGATIVE", negative)

    badge_by_label = {"Positive": "buy", "Negative": "sell", "Neutral": "hold"}
    for item in scored:
        st.markdown(_headline_html(item, badge_by_label[item["Label"]]), unsafe_allow_html=True)


def _render_fundamentals(ticker):
    st.subheader("Quarterly results & analyst view", help=HELP["fundamentals"])
    try:
        fundamentals = cached_fundamentals(ticker)
    except Exception as error:
        st.info(f"Fundamentals unavailable: {error}")
        return
    if not fundamentals:
        st.info("No fundamentals data returned by Yahoo Finance for this ticker.")
        return

    growth = fundamentals.get("Revenue Growth QoQ")
    target = fundamentals.get("Analyst Target")
    cols = st.columns(4)
    cols[0].metric("REVENUE GROWTH · QoQ", f"{growth:+.1%}" if growth == growth else "—")
    cols[1].metric("ANALYST TARGET", f"₹{target:,.2f}" if target else "—")
    cols[2].metric("ANALYST RATING", (fundamentals.get("Analyst Recommendation") or "—").upper())
    cols[3].metric("ANALYSTS COVERING", fundamentals.get("Analyst Count") or "—")

    revenue = fundamentals.get("Quarterly Revenue")
    if revenue is not None and not revenue.empty:
        show(revenue_chart(revenue), f"{ticker}-revenue")


def _render_backtest(ticker, data):
    st.subheader("Strategy backtest", help=HELP["backtest"])
    try:
        equity, summary = run_backtest(data)
    except Exception as error:
        st.info(f"Backtest unavailable: {error}")
        return

    cols = st.columns(5)
    cols[0].metric("STRATEGY RETURN", f"{summary['Strategy Return %']:+.1f}%")
    cols[1].metric("BUY & HOLD RETURN", f"{summary['Buy & Hold Return %']:+.1f}%")
    cols[2].metric("SHARPE", f"{summary['Sharpe']:.2f}")
    cols[3].metric("MAX DRAWDOWN", f"{summary['Max Drawdown %']:.1f}%")
    cols[4].metric("TRADES", summary["Trades"])
    show(backtest_equity_chart(equity), f"{ticker}-backtest", height=380)


def render_company(ticker, name, horizon):
    try:
        with st.spinner(f"Running forecast for {ticker}..."):
            data, bands, summary = company_forecast(ticker, name, horizon)
    except Exception as error:
        st.warning(f"Could not build a forecast for {ticker}: {error}")
        return

    overview_tab, news_tab, fundamentals_tab, backtest_tab, intraday_tab = st.tabs(
        ["Overview & verdict", "News & sentiment", "Fundamentals", "Backtest", "Intraday feed"]
    )
    with overview_tab:
        _render_overview(ticker, horizon, data, bands, summary)
    with news_tab:
        _render_news(ticker, name)
    with fundamentals_tab:
        _render_fundamentals(ticker)
    with backtest_tab:
        _render_backtest(ticker, data)
    with intraday_tab:
        st.subheader("Intraday live feed", help=HELP["intraday"])
        render_market(ticker)


def render_macro():
    st.subheader("Macro, policy & geopolitical headlines", help=HELP["macro"])
    articles = cached_macro_news()
    if not articles:
        st.info("No macro headlines available right now.")
        return
    for item in articles:
        st.markdown(_headline_html(item), unsafe_allow_html=True)


@st.fragment(run_every=60)
def render_market(ticker):
    bars = read_bars(ticker, DATA_DIR)
    if bars.empty:
        st.info("Feed requested. Waiting for the first yfinance bars to arrive through Kafka.")
        return

    analyzed, summary = analyze_bars(bars)
    updated = bars.index[-1].tz_convert("Asia/Kolkata").strftime("%d %b %Y · %H:%M IST")
    signal_class = summary["Signal"].lower()
    st.markdown(
        f'<span class="signal {signal_class}">{summary["Signal"]}</span> '
        f'<span class="eyebrow">INTRADAY CONSENSUS · MARKOV + MACD + RSI + BOLLINGER</span>',
        unsafe_allow_html=True,
    )
    metrics = st.columns(4)
    metrics[0].metric("LAST TRADED", f"₹{summary['Last Price']:,.2f}", help="Latest one-minute close.")
    metrics[1].metric(
        "MARKOV NEXT BAR",
        f"{summary['Expected Return %']:+.4f}%",
        help="Expected next-minute return from an UP/DOWN/SIDEWAYS Markov chain fitted to recent bars.",
    )
    rsi = summary["RSI"]
    metrics[2].metric("RSI · 14", f"{rsi:.1f}" if rsi == rsi else "—", help=HELP["rsi"])
    metrics[3].metric("LATEST BAR", updated)

    st.plotly_chart(
        intraday_chart(bars, analyzed), use_container_width=True, config={"displaylogo": False}, key=f"{ticker}-intraday"
    )
    st.caption(
        f"{len(bars):,} stored one-minute bars · Forecast reference ₹{summary['Forecast Price']:,.2f} · "
        f"Signal score {summary['Score']:+d}"
    )


def _render_sidebar():
    st.sidebar.markdown('<div class="eyebrow">MARKET PULSE / NSE + BSE</div>', unsafe_allow_html=True)
    st.sidebar.header("Find a company")
    with st.sidebar.form("company-search"):
        query = st.text_input("Ticker or company name", placeholder="HCLTECH or Tata Motors")
        search_clicked = st.form_submit_button("Search Yahoo Finance", use_container_width=True)

    if search_clicked:
        with st.spinner("Searching Yahoo Finance..."):
            st.session_state["search_results"] = cached_search(query) if query.strip() else []

    watchlist = st.session_state.setdefault("watchlist", {})
    search_results = st.session_state.get("search_results", [])
    if search_results:
        symbol_names = {item["symbol"]: item["name"] for item in search_results}
        selected = st.sidebar.selectbox(
            "NSE / BSE matches",
            list(symbol_names),
            format_func=lambda symbol: f"{symbol_names[symbol]}  ·  {symbol}",
        )
        if st.sidebar.button("Add to dashboard", type="primary", use_container_width=True):
            watchlist[selected] = symbol_names[selected].split(" · ")[0]
            try:
                producer = get_kafka_producer()
                producer.produce(SUBSCRIPTION_TOPIC, value=json.dumps({"ticker": selected}).encode("utf-8"))
                if producer.flush(15):
                    raise TimeoutError("Kafka did not acknowledge the ticker subscription")
                st.sidebar.success(f"{selected} added with live intraday feed")
            except Exception as error:
                st.sidebar.warning(f"{selected} added; intraday feed unavailable (Kafka): {error}")
    elif search_clicked:
        st.sidebar.warning("No NSE or BSE match found. Try a Yahoo Finance ticker such as HCLTECH.NS.")

    st.sidebar.divider()
    horizon = st.sidebar.slider(
        "Forecast horizon (trading sessions)",
        min_value=5,
        max_value=90,
        value=30,
        step=5,
        help="How far ahead the Monte Carlo simulation projects prices. Longer horizons widen the uncertainty bands.",
    )
    st.sidebar.caption("Yahoo Finance · 2Y daily history for forecasts · 1-minute bars for the intraday feed")
    return watchlist, horizon


def run():
    st.markdown(CSS, unsafe_allow_html=True)
    watchlist, horizon = _render_sidebar()

    st.markdown('<div class="eyebrow">INDIA EQUITIES / FORECAST DESK</div>', unsafe_allow_html=True)
    st.title("Market Pulse")
    st.markdown(
        '<div class="market-note">Forecasts combine Monte Carlo simulation, trend, momentum, mean-reversion, '
        "risk, news sentiment and earnings models on Yahoo Finance and Google News data, which may be delayed. "
        "They are probabilistic estimates, not guarantees or investment advice.</div>",
        unsafe_allow_html=True,
    )

    companies = list(watchlist.items())
    if len(companies) > 1:
        render_scorecard(watchlist, horizon)

    tab_labels = ["Macro & policy"] + [f"{name} · {ticker}" for ticker, name in companies]
    tabs = st.tabs(tab_labels)
    with tabs[0]:
        render_macro()

    if not companies:
        st.info("Search for an Indian company or ticker, then add it to the dashboard to see its forecast.")
        return

    for tab, (ticker, name) in zip(tabs[1:], companies):
        with tab:
            render_company(ticker, name, horizon)
            if st.button("Remove from dashboard", key=f"remove-{ticker}"):
                del watchlist[ticker]
                st.rerun()
