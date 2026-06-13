from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"

def plot_equity_curve(df: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["equity"], name="Equity", line=dict(color="#01696f", width=2)))
    fig.update_layout(
        title="Equity Curve (15-Year Backtest)",
        xaxis_title="Date",
        yaxis_title="Cumulative Return",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="perplexity",
        height=500
    )
    fig.write_image(OUT / "equity_curve.png")
    with open(OUT / "equity_curve.png.meta.json", "w") as f:
        json.dump({"caption": "Equity Curve", "description": "15-year cumulative equity trajectory"}, f)


def plot_monthly_returns(df: pd.DataFrame):
    monthly = df.set_index("date")["ret"].resample("M").apply(lambda x: (1 + x).prod() - 1)
    fig = go.Figure()
    colors = ["#01696f" if r > 0 else "#a12c7b" for r in monthly]
    fig.add_trace(go.Bar(x=monthly.index, y=monthly, name="Monthly Return", color=colors))
    fig.update_layout(
        title="Monthly Returns Distribution",
        xaxis_title="Month",
        yaxis_title="Return (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="perplexity",
        height=500
    )
    fig.write_image(OUT / "monthly_returns.png")
    with open(OUT / "monthly_returns.png.meta.json", "w") as f:
        json.dump({"caption": "Monthly Returns", "description": "Monthly return bars by color"}, f)


def plot_drawdown(df: pd.DataFrame):
    cummax = df["equity"].cummax()
    dd = df["equity"] / cummax - 1
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=dd, name="Drawdown", fill="tozeroid", line=dict(color="#a12c7b", width=1.5)))
    fig.update_layout(
        title="Drawdown Over Time",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="perplexity",
        height=500
    )
    fig.write_image(OUT / "drawdown.png")
    with open(OUT / "drawdown.png.meta.json", "w") as f:
        json.dump({"caption": "Drawdown", "description": "Drawdown percentage over time"}, f)


def plot_trade_distribution(trades: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=trades["ret"], name="Trade Returns", nbinsx=30, color="#01696f"))
    fig.update_layout(
        title="Trade Return Distribution",
        xaxis_title="Return (%)",
        yaxis_title="Count",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="perplexity",
        height=500
    )
    fig.write_image(OUT / "trade_distribution.png")
    with open(OUT / "trade_distribution.png.meta.json", "w") as f:
        json.dump({"caption": "Trade Distribution", "description": "Histogram of trade returns"}, f)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ret_df = pd.read_csv(OUT / "backtest_daily_returns.csv")
    trades = pd.read_csv(OUT / "backtest_trades.csv")
    plot_equity_curve(ret_df)
    plot_monthly_returns(ret_df)
    plot_drawdown(ret_df)
    plot_trade_distribution(trades)
    print("Charts saved to output/")


if __name__ == "__main__":
    main()
