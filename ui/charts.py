import plotly.graph_objects as go
from plotly.subplots import make_subplots


def gauge_chart(score, max_score):
    return go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": f" / {max_score}", "font": {"size": 34}},
            gauge={
                "axis": {"range": [-max_score, max_score], "tickvals": [-max_score, -2, 0, 2, max_score]},
                "bar": {"color": "#e7eee8", "thickness": 0.25},
                "bgcolor": "#151d17",
                "steps": [
                    {"range": [-max_score, -1.5], "color": "#402823"},
                    {"range": [-1.5, 1.5], "color": "#39351f"},
                    {"range": [1.5, max_score], "color": "#223b27"},
                ],
            },
        )
    )


def forecast_chart(data, bands):
    history = data["Close"].tail(120)
    fig = go.Figure()
    for upper, lower, fill, label in [
        ("P95", "P5", "rgba(167,207,138,0.12)", "90% range"),
        ("P75", "P25", "rgba(167,207,138,0.25)", "50% range"),
    ]:
        fig.add_trace(go.Scatter(x=bands.index, y=bands[upper], name=upper, line={"width": 0}, showlegend=False))
        fig.add_trace(go.Scatter(x=bands.index, y=bands[lower], name=label, fill="tonexty", fillcolor=fill, line={"width": 0}))
    fig.add_trace(go.Scatter(x=history.index, y=history, name="Close", line={"color": "#e7eee8", "width": 1.6}))
    fig.add_trace(
        go.Scatter(
            x=[history.index[-1], *bands.index],
            y=[history.iloc[-1], *bands["P50"]],
            name="Median forecast",
            line={"color": "#a7cf8a", "width": 2, "dash": "dash"},
        )
    )
    fig.update_yaxes(title_text="Price (₹)")
    return fig


def trend_chart(data):
    recent = data.tail(252)
    fig = go.Figure(
        go.Candlestick(
            x=recent.index,
            open=recent["Open"],
            high=recent["High"],
            low=recent["Low"],
            close=recent["Close"],
            name="Price",
            increasing_line_color="#a7cf8a",
            decreasing_line_color="#ed8879",
        )
    )
    for column, color in [("SMA 50", "#e2b875"), ("SMA 200", "#8ab8a0")]:
        fig.add_trace(go.Scatter(x=recent.index, y=recent[column], name=column, line={"color": color, "width": 1.5}))
    fig.update_layout(xaxis_rangeslider_visible=False)
    return fig


def momentum_chart(momentum):
    labels = [period for period, value in momentum.items() if value == value]
    values = [momentum[period] for period in labels]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=["#a7cf8a" if value >= 0 else "#ed8879" for value in values],
            text=[f"{value:+.1%}" for value in values],
            textposition="outside",
            name="Return",
        )
    )
    fig.update_yaxes(tickformat=".0%")
    return fig


def drawdown_chart(data):
    drawdown = data["Drawdown"].tail(252)
    fig = go.Figure(
        go.Scatter(
            x=drawdown.index,
            y=drawdown,
            name="Drawdown",
            fill="tozeroy",
            fillcolor="rgba(237,136,121,0.2)",
            line={"color": "#ed8879", "width": 1.2},
        )
    )
    fig.update_yaxes(tickformat=".0%")
    return fig


def distribution_chart(data, value_at_risk):
    fig = go.Figure(go.Histogram(x=data["Return"].tail(252).dropna(), nbinsx=50, name="Days", marker_color="#688a6f"))
    fig.add_vline(x=-value_at_risk, line_dash="dot", line_color="#ed8879", annotation_text="95% VaR")
    fig.update_xaxes(tickformat=".1%")
    return fig


def rsi_chart(data):
    rsi = data["RSI"].tail(252)
    fig = go.Figure(go.Scatter(x=rsi.index, y=rsi, name="RSI 14", line={"color": "#8ab8a0", "width": 1.5}))
    for level in [30, 70]:
        fig.add_hline(y=level, line_dash="dot", line_color="#59675d")
    fig.update_yaxes(range=[0, 100])
    return fig


def revenue_chart(revenue):
    labels = [str(period.date()) if hasattr(period, "date") else str(period) for period in revenue.index]
    fig = go.Figure(go.Bar(x=labels, y=revenue.values, marker_color="#a7cf8a", name="Quarterly revenue"))
    fig.update_yaxes(title_text="Revenue (₹)")
    return fig


def backtest_equity_chart(equity):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=equity.index, y=equity["Strategy"], name="Strategy", line={"color": "#a7cf8a", "width": 1.8}))
    fig.add_trace(
        go.Scatter(x=equity.index, y=equity["Buy & Hold"], name="Buy & hold", line={"color": "#8ab8a0", "width": 1.2, "dash": "dot"})
    )
    fig.update_yaxes(title_text="Portfolio value (₹)")
    return fig


def intraday_chart(bars, analyzed):
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.035,
        row_heights=[0.6, 0.22, 0.18],
    )
    fig.add_trace(
        go.Candlestick(
            x=bars.index,
            open=bars["Open"],
            high=bars["High"],
            low=bars["Low"],
            close=bars["Close"],
            name="Price",
            increasing_line_color="#a7cf8a",
            decreasing_line_color="#ed8879",
        ),
        row=1,
        col=1,
    )
    for column, color, name in [
        ("BB Upper", "#849888", "Upper band"),
        ("BB Lower", "#849888", "Lower band"),
    ]:
        fig.add_trace(
            go.Scatter(x=analyzed.index, y=analyzed[column], name=name, line={"color": color, "width": 1, "dash": "dot"}),
            row=1,
            col=1,
        )

    histogram = analyzed["MACD"] - analyzed["MACD Signal"]
    fig.add_trace(go.Bar(x=analyzed.index, y=histogram, name="MACD spread", marker_color="#688a6f"), row=2, col=1)
    fig.add_trace(go.Scatter(x=analyzed.index, y=analyzed["MACD"], name="MACD", line={"color": "#a7cf8a", "width": 1.5}), row=2, col=1)
    fig.add_trace(
        go.Scatter(x=analyzed.index, y=analyzed["MACD Signal"], name="Signal line", line={"color": "#e2b875", "width": 1.2}),
        row=2,
        col=1,
    )
    fig.add_trace(go.Scatter(x=analyzed.index, y=analyzed["RSI"], name="RSI", line={"color": "#8ab8a0", "width": 1.5}), row=3, col=1)
    for level in [30, 70]:
        fig.add_hline(y=level, line_dash="dot", line_color="#59675d", row=3, col=1)

    fig.update_layout(
        template="plotly_dark",
        height=760,
        margin={"l": 12, "r": 12, "t": 25, "b": 12},
        paper_bgcolor="#151d17",
        plot_bgcolor="#151d17",
        font={"family": "DM Mono, monospace", "color": "#cbd7cd", "size": 11},
        legend={"orientation": "h", "y": 1.02, "x": 0},
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#27332a")
    fig.update_yaxes(showgrid=True, gridcolor="#27332a")
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="MACD", row=2, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=3, col=1)
    return fig
