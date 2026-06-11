from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

from scripts.utils import load_config, ensure_dir, read_universe, annualized_return, sharpe_ratio, sortino_ratio, max_drawdown
from scripts.data_loader import fetch_symbol_history
from scripts.strategy import compute_features

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"


def select_daily_candidates(feature_panel: dict, current_date: pd.Timestamp, cfg: dict, meta: pd.DataFrame):
    rows = []
    for symbol, df in feature_panel.items():
        sub = df[df["date"] <= current_date]
        if len(sub) < cfg["universe"]["min_history_days"]:
            continue
        r = sub.dropna().iloc[-1] if len(sub.dropna()) else None
        if r is None:
            continue
        if not (r["close"] > r["ma50"] > r["ma200"]):
            continue
        score = 0.30 * 1.0 + 0.25 * max(0, r["ret_60"]) + 0.20 * max(0, r["ret_120"]) + 0.15 * max(0, -r["z20"]) + 0.10 * (1 - min(1, r["atr_pct"] / 0.08))
        rows.append({"symbol": symbol, "score": score, "close": r["close"]})
    if not rows:
        return pd.DataFrame(columns=["symbol", "score", "close"])
    out = pd.DataFrame(rows).sort_values("score", ascending=False).head(cfg["universe"]["max_positions"])
    return out


def main():
    cfg = load_config()
    ensure_dir(OUT)
    universe = read_universe(ROOT / cfg["universe"]["file"])
    panel = {}
    for _, row in universe.iterrows():
        raw = fetch_symbol_history(row["symbol"], row.get("yf_symbol"), cfg["market"]["start_date"], cfg["market"]["end_date"])
        if len(raw) >= cfg["universe"]["min_history_days"]:
            panel[row["symbol"]] = compute_features(raw, cfg)

    all_dates = sorted(set(pd.concat([df["date"] for df in panel.values()]).dropna().tolist()))
    rets = []
    holdings = []
    max_hold = cfg["execution"]["hold_max_days"]

    for i, dt in enumerate(all_dates[:-max_hold-1]):
        picks = select_daily_candidates(panel, dt, cfg, universe)
        if picks.empty:
            rets.append({"date": dt, "ret": 0.0})
            continue
        future_returns = []
        for _, row in picks.iterrows():
            df = panel[row["symbol"]]
            sub = df[df["date"] >= dt].reset_index(drop=True)
            if len(sub) <= max_hold:
                continue
            entry = sub.loc[0, "close"]
            stop = entry - cfg["risk"]["stop_atr_multiple"] * sub.loc[0, "atr14"]
            exit_px = sub.loc[max_hold, "close"]
            hold_days = max_hold
            for j in range(1, min(max_hold, len(sub)-1) + 1):
                px = sub.loc[j, "close"]
                trail = max(stop, px - cfg["risk"]["trailing_stop_atr_multiple"] * sub.loc[j, "atr14"])
                if px <= stop or px <= trail:
                    exit_px = px
                    hold_days = j
                    break
            gross = exit_px / entry - 1
            net = gross - (cfg["execution"]["slippage_bps"] + cfg["execution"]["cost_bps"]) / 10000
            future_returns.append(net)
            holdings.append({"date": dt, "symbol": row["symbol"], "entry": entry, "exit": exit_px, "hold_days": hold_days, "ret": net})
        rets.append({"date": dt, "ret": float(np.mean(future_returns)) if future_returns else 0.0})

    ret_df = pd.DataFrame(rets).sort_values("date")
    ret_df["equity"] = (1 + ret_df["ret"]).cumprod()
    metrics = pd.DataFrame([{
        "CAGR": annualized_return(ret_df["ret"]),
        "Sharpe": sharpe_ratio(ret_df["ret"]),
        "Sortino": sortino_ratio(ret_df["ret"]),
        "MaxDrawdown": max_drawdown(ret_df["equity"]),
        "WinRate": (pd.DataFrame(holdings)["ret"] > 0).mean() if holdings else np.nan,
        "AvgHoldDays": pd.DataFrame(holdings)["hold_days"].mean() if holdings else np.nan,
        "Trades": len(holdings)
    }])

    ret_df.to_csv(OUT / "backtest_daily_returns.csv", index=False)
    pd.DataFrame(holdings).to_csv(OUT / "backtest_trades.csv", index=False)
    metrics.to_csv(OUT / "backtest_metrics.csv", index=False)
    print(metrics.to_dict(orient="records")[0])


if __name__ == "__main__":
    main()
