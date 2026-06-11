from __future__ import annotations
import os
import yaml
import math
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_config():
    with open(ROOT / "config" / "strategy.yml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def read_universe(path):
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    return df


def rsi(series, window=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(df, window=14):
    high = df["high"]
    low = df["low"]
    close = df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(window).mean()


def annualized_return(daily_returns):
    if len(daily_returns) == 0:
        return np.nan
    total = (1 + daily_returns).prod()
    years = len(daily_returns) / 252
    return total ** (1 / years) - 1 if years > 0 else np.nan


def sharpe_ratio(daily_returns, rf=0.0):
    if len(daily_returns) < 2:
        return np.nan
    excess = daily_returns - rf / 252
    std = excess.std(ddof=0)
    return np.sqrt(252) * excess.mean() / std if std > 0 else np.nan


def sortino_ratio(daily_returns, rf=0.0):
    if len(daily_returns) < 2:
        return np.nan
    excess = daily_returns - rf / 252
    downside = excess[excess < 0].std(ddof=0)
    return np.sqrt(252) * excess.mean() / downside if downside and downside > 0 else np.nan


def max_drawdown(equity_curve):
    cummax = equity_curve.cummax()
    dd = equity_curve / cummax - 1
    return dd.min()
