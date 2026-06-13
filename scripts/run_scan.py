from __future__ import annotations
import os
from pathlib import Path
import pandas as pd
from datetime import datetime
from jinja2 import Template

from scripts.utils import load_config, ensure_dir, read_universe
from scripts.data_loader import fetch_symbol_history
from scripts.strategy import compute_features, latest_signal_row
from scripts.emailer import send_email

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"


def normalize_columns(df):
    """Normalize column names to lowercase and handle common variations."""
    if df.empty:
        return df
    df.columns = df.columns.str.lower().str.strip()
    return df


def build_sector_scores(universe, hist_map):
    sector_scores = {}
    for sector, g in universe.groupby("sector"):
        vals = []
        for _, row in g.iterrows():
            df = hist_map.get(row["symbol"])
            if df is None or len(df) < 130:
                continue
            if "close" not in df.columns:
                print(f"Warning: 'close' column not found for {row['symbol']}. Available columns: {list(df.columns)}")
                continue
            ret60 = df["close"].pct_change(60).iloc[-1]
            ma100 = df["close"].rolling(100).mean().iloc[-1]
            close = df["close"].iloc[-1]
            vals.append((ret60, float(close > ma100)))
        if vals:
            ret_mean = pd.Series([x[0] for x in vals]).mean()
            trend_mean = pd.Series([x[1] for x in vals]).mean()
            sector_scores[sector] = max(0.0, min(1.0, (ret_mean + 0.05) / 0.25)) * 0.7 + trend_mean * 0.3
        else:
            sector_scores[sector] = 0.0
    return sector_scores


def main():
    cfg = load_config()
    ensure_dir(OUT)
    universe = read_universe(ROOT / cfg["universe"]["file"])
    hist_map = {}

    for _, row in universe.iterrows():
        df = fetch_symbol_history(row["symbol"], row.get("yf_symbol"), cfg["market"]["start_date"], cfg["market"]["end_date"])
        df = normalize_columns(df)
        if len(df) >= cfg["universe"]["min_history_days"]:
            hist_map[row["symbol"]] = df

    sector_scores = build_sector_scores(universe, hist_map)
    rows = []
    for _, row in universe.iterrows():
        sym = row["symbol"]
        df = hist_map.get(sym)
        if df is None:
            continue
        feat = compute_features(df, cfg)
        sig = latest_signal_row(feat, sector_scores.get(row["sector"], 0.0), cfg)
        if not sig:
            continue
        sig["symbol"] = sym
        sig["sector"] = row["sector"]
        sig["industry"] = row.get("industry", "")
        rows.append(sig)

    out = pd.DataFrame(rows)
    if out.empty:
        out = pd.DataFrame(columns=["symbol", "sector", "industry", "composite_score"])
    else:
        # Normalize output columns
        out.columns = out.columns.str.lower().str.strip()
        
        # Ensure required columns exist before filtering
        required_cols = ["close", "median_turnover_cr", "trend_ok", "composite_score", "ret_60", "sector_score", "z20"]
        missing_cols = [col for col in required_cols if col not in out.columns]
        if missing_cols:
            print(f"Warning: Missing columns in output: {missing_cols}")
            print(f"Available columns: {list(out.columns)}")
        
        out = out[
            (out["close"] >= cfg["universe"]["min_price"]) &
            (out["median_turnover_cr"] >= cfg["universe"]["min_median_turnover_cr"]) &
            (out["trend_ok"] == 1)
        ].sort_values(["composite_score", "ret_60", "sector_score"], ascending=False)
        out["rank"] = range(1, len(out) + 1)
        out["position_size_pct"] = (cfg["risk"]["max_single_position_weight"] * 100).round(2)
        out["setup_type"] = out["z20"].apply(lambda z: "Trend Pullback" if z < -0.5 else "Trend Continuation")

    csv_path = OUT / "screened_stocks.csv"
    html_path = OUT / "screened_stocks.html"
    sector_csv = OUT / "sector_leadership.csv"
    setup_csv = OUT / "setup_mix.csv"
    out.to_csv(csv_path, index=False)

    top = out.head(cfg["email"]["top_n_rows"]).copy()
    table_html = top.to_html(index=False, float_format=lambda x: f"{x:.4f}")
    html_path.write_text(table_html, encoding="utf-8")

    sector_df = (out.groupby('sector', dropna=False)
                   .agg(stock_count=('symbol','count'), avg_score=('composite_score','mean'), avg_ret_60=('ret_60','mean'))
                   .sort_values(['avg_score','avg_ret_60'], ascending=False)
                   .reset_index()) if not out.empty else pd.DataFrame(columns=['sector','stock_count','avg_score','avg_ret_60'])
    sector_df.to_csv(sector_csv, index=False)
    sector_table_html = sector_df.to_html(index=False, float_format=lambda x: f"{x:.4f}")

    setup_df = (out.groupby('setup_type', dropna=False)
                  .agg(stock_count=('symbol','count'), avg_score=('composite_score','mean'), avg_ret_60=('ret_60','mean'))
                  .sort_values('stock_count', ascending=False)
                  .reset_index()) if not out.empty else pd.DataFrame(columns=['setup_type','stock_count','avg_score','avg_ret_60'])
    setup_df.to_csv(setup_csv, index=False)
    setup_table_html = setup_df.to_html(index=False, float_format=lambda x: f"{x:.4f}")

    template = Template((ROOT / "templates" / "email_report.html.j2").read_text(encoding="utf-8"))
    subject = f'{cfg["email"]["subject_prefix"]} | {datetime.now().strftime("%Y-%m-%d")}'
    top_score = f"{top['composite_score'].max():.3f}" if not top.empty else 'NA'
    median_ret_60 = f"{100*top['ret_60'].median():.2f}%" if not top.empty else 'NA'
    top_sector = str(sector_df.iloc[0]['sector']) if not sector_df.empty else 'NA'
    setup_mix = ', '.join([f"{r.setup_type}:{int(r.stock_count)}" for r in setup_df.itertuples(index=False)]) if not setup_df.empty else 'NA'
    html_body = template.render(
        subject=subject,
        run_time=datetime.now().isoformat(sep=" ", timespec="seconds"),
        universe_size=len(universe),
        selected_size=len(out),
        top_score=top_score,
        median_ret_60=median_ret_60,
        top_sector=top_sector,
        setup_mix=setup_mix,
        table_html=table_html,
        sector_table_html=sector_table_html,
        setup_table_html=setup_table_html,
    )

    to_addr = os.environ.get("EMAIL_TO", cfg["email"]["default_to"])
    if all(os.environ.get(k) for k in ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS"]):
        send_email(subject, html_body, to_addr, [str(csv_path)])
    else:
        print("SMTP secrets not configured; skipped email send.")


if __name__ == "__main__":
    main()
