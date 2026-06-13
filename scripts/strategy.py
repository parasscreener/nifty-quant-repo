from __future__ import annotations
import numpy as np
import pandas as pd
from scripts.utils import atr, rsi


def compute_features(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    s = cfg["signals"]
    out = df.copy().sort_values("date")
    out["ret_5"] = out["close"].pct_change(5)
    out["ret_20"] = out["close"].pct_change(20)
    out["ret_60"] = out["close"].pct_change(s["momentum_lookback_1"])
    out["ret_120"] = out["close"].pct_change(s["momentum_lookback_2"])
    out["ma20"] = out["close"].rolling(s["ma_fast"]).mean()
    out["ma50"] = out["close"].rolling(s["ma_mid"]).mean()
    out["ma200"] = out["close"].rolling(s["ma_slow"]).mean()
    out["std20"] = out["close"].rolling(s["reversal_z_window"]).std()
    out["z20"] = (out["close"] - out["ma20"]) / out["std20"]
    out["breakout_55"] = out["close"] / out["close"].rolling(s["breakout_window"]).max() - 1
    out["atr14"] = atr(out, s["atr_window"])
    out["atr_pct"] = out["atr14"] / out["close"]
    out["rsi14"] = rsi(out["close"], 14)
    out["vol20"] = out["close"].pct_change().rolling(s["vol_window"]).std()
    out["median_turnover"] = ((out["close"] * out["volume"]) / 1e7).rolling(20).median()
    return out


def latest_signal_row(df: pd.DataFrame, sector_score: float, cfg: dict) -> dict | None:
    w = cfg["weights"]
    r = df.dropna().iloc[-1] if len(df.dropna()) else None
    if r is None:
        return None
    trend_ok = int(r["close"] > r["ma50"] > r["ma200"])
    breakout_ok = int(r["breakout_55"] >= -0.02)
    reversal_score = max(0.0, min(1.0, (-r["z20"] - 0.5) / 2.0)) if r["z20"] < -0.5 else 0.0
    vol_penalty = max(0.0, min(1.0, r["atr_pct"] / 0.08))
    momentum60 = max(0.0, min(1.0, (r["ret_60"] + 0.05) / 0.30))
    momentum120 = max(0.0, min(1.0, (r["ret_120"] + 0.08) / 0.50))
    score = (
        w["trend"] * trend_ok +
        w["momentum_60"] * momentum60 +
        w["momentum_120"] * momentum120 +
        w["reversal"] * reversal_score +
        w["breakout"] * breakout_ok +
        w["sector_strength"] * sector_score +
        w["volatility_penalty"] * (1 - vol_penalty)
    )
    stop_loss = r["close"] - cfg["risk"]["stop_atr_multiple"] * r["atr14"]
    trailing = r["close"] - cfg["risk"]["trailing_stop_atr_multiple"] * r["atr14"]
    return {
        "date": r["date"],
        "close": float(r["close"]),
        "ret_20": float(r["ret_20"]),
        "ret_60": float(r["ret_60"]),
        "ret_120": float(r["ret_120"]),
        "ma20": float(r["ma20"]),
        "ma50": float(r["ma50"]),
        "ma200": float(r["ma200"]),
        "z20": float(r["z20"]),
        "rsi14": float(r["rsi14"]),
        "atr_pct": float(r["atr_pct"]),
        "breakout_55": float(r["breakout_55"]),
        "median_turnover_cr": float(r["median_turnover"]),
        "sector_score": float(sector_score),
        "trend_ok": trend_ok,
        "composite_score": float(score),
        "entry_rule": "Trend + RS + sector strength, optionally short-term pullback",
        "exit_rule": "2 ATR hard stop, 3 ATR trail, signal decay, or max hold",
        "stop_loss": float(stop_loss),
        "trailing_stop": float(trailing),
        "hold_min_days": cfg["execution"]["hold_min_days"],
        "hold_max_days": cfg["execution"]["hold_max_days"],
    }
