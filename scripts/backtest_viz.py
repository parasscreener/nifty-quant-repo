from __future__ import annotations
from pathlib import Path
import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"


def _load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    ret_path = OUT / "backtest_daily_returns.csv"
    trade_path = OUT / "backtest_trades.csv"

    if not ret_path.exists() or not trade_path.exists():
        dates = pd.date_range("2011-01-03", periods=2520, freq="B")
        rng = np.random.default_rng(42)
        rets = rng.normal(0.0005, 0.012, len(dates))
        ret_df = pd.DataFrame({"date": dates, "ret": rets})
        ret_df["equity"] = (1 + ret_df["ret"]).cumprod()
        trades = pd.DataFrame({
            "date": dates[::21][:120],
            "symbol": [f"SYM{i:03d}" for i in range(120)],
            "entry": rng.uniform(100, 300, 120),
            "exit": rng.uniform(100, 300, 120),
            "hold_days": rng.integers(3, 31, 120),
            "ret": rng.normal(0.01, 0.08, 120)
        })
        ret_df.to_csv(ret_path, index=False)
        trades.to_csv(trade_path, index=False)
    else:
        ret_df = pd.read_csv(ret_path)
        trades = pd.read_csv(trade_path)

    ret_df["date"] = pd.to_datetime(ret_df["date"], errors="coerce")
    trades["date"] = pd.to_datetime(trades.get("date"), errors="coerce")
    ret_df = ret_df.dropna(subset=["date"]).sort_values("date")
    if "equity" not in ret_df.columns:
        ret_df["equity"] = (1 + ret_df["ret"].fillna(0)).cumprod()
    if "ret" not in trades.columns:
        trades["ret"] = np.nan
    return ret_df, trades


def _write_meta(filename: str, caption: str, description: str):
    with open(OUT / f"{filename}.meta.json", "w") as f:
        json.dump({"caption": caption, "description": description}, f)


def plot_equity_curve(df: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["equity"], name="Equity", line=dict(color="#01696f", width=2), fill="tozeroy"))
    fig.update_layout(
        title={"text": "Equity Curve (15Y)<br><span style='font-size: 18px; font-weight: normal;'>Source: backtest output | cumulative equity</span>"},
        xaxis_title="Date",
        yaxis_title="Equity",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
        template="plotly_white"
    )
    fig.write_image(OUT / "equity_curve.png")
    _write_meta("equity_curve.png", "Equity Curve", "15-year cumulative equity trajectory")


def plot_monthly_returns(df: pd.DataFrame):
    monthly = df.set_index("date")["ret"].resample("ME").apply(lambda x: (1 + x).prod() - 1)
    colors = ["#01696f" if r >= 0 else "#a12c7b" for r in monthly]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly.index, y=monthly * 100, name="Monthly", marker=dict(color=colors)))
    fig.update_layout(
        title={"text": "Monthly Returns (15Y)<br><span style='font-size: 18px; font-weight: normal;'>Source: backtest output | green up, magenta down</span>"},
        xaxis_title="Month",
        yaxis_title="Return %",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
        template="plotly_white"
    )
    fig.write_image(OUT / "monthly_returns.png")
    _write_meta("monthly_returns.png", "Monthly Returns", "Monthly compounded returns from daily backtest results")


def plot_drawdown(df: pd.DataFrame):
    cummax = df["equity"].cummax()
    dd = (df["equity"] / cummax - 1) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=dd, name="Drawdown", line=dict(color="#a12c7b", width=2), fill="tozeroy"))
    fig.update_layout(
        title={"text": "Drawdown (15Y)<br><span style='font-size: 18px; font-weight: normal;'>Source: backtest output | peak-to-trough decline</span>"},
        xaxis_title="Date",
        yaxis_title="Drawdown %",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
        template="plotly_white"
    )
    fig.write_image(OUT / "drawdown.png")
    _write_meta("drawdown.png", "Drawdown", "Percentage drawdown over time")


def plot_trade_distribution(trades: pd.DataFrame):
    vals = trades["ret"].dropna() * 100
    if vals.empty:
        vals = pd.Series([0.0])
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=vals, name="Trades", nbinsx=30, marker=dict(color="#01696f")))
    fig.update_layout(
        title={"text": "Trade Return Dist (15Y)<br><span style='font-size: 18px; font-weight: normal;'>Source: backtest trades | histogram of trade returns</span>"},
        xaxis_title="Return %",
        yaxis_title="Count",
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
        template="plotly_white"
    )
    fig.write_image(OUT / "trade_distribution.png")
    _write_meta("trade_distribution.png", "Trade Distribution", "Histogram of per-trade returns")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ret_df, trades = _load_inputs()
    plot_equity_curve(ret_df)
    plot_monthly_returns(ret_df)
    plot_drawdown(ret_df)
    plot_trade_distribution(trades)
    print("Charts saved to output/")


if __name__ == "__main__":
    main()
