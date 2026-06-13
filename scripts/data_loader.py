from __future__ import annotations
import warnings
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

try:
    from NSEDownload import stocks
except Exception:
    stocks = None


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    # Flatten MultiIndex columns if they exist
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in df.columns]
    
    # Now safely call .lower() on column names
    cols = {c.lower(): c for c in df.columns}
    rename_map = {}
    for c in df.columns:
        cl = c.lower()
        if cl in ["date"]: rename_map[c] = "date"
        elif cl in ["open"]: rename_map[c] = "open"
        elif cl in ["high"]: rename_map[c] = "high"
        elif cl in ["low"]: rename_map[c] = "low"
        elif cl in ["close", "adj close", "adj_close"]: rename_map[c] = "close"
        elif cl in ["volume", "shares traded", "shares_traded"]: rename_map[c] = "volume"
    df = df.rename(columns=rename_map)
    needed = ["date", "open", "high", "low", "close", "volume"]
    if "date" not in df.columns:
        df = df.reset_index().rename(columns={df.index.name or "index": "date"})
        if "date" not in df.columns and "Date" in df.columns:
            df = df.rename(columns={"Date": "date"})
    df = df[[c for c in needed if c in df.columns]].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    return df.sort_values("date").drop_duplicates("date")


def fetch_symbol_history(symbol: str, yf_symbol: str | None, start_date: str, end_date: str | None):
    if stocks is not None:
        try:
            raw = stocks.get_adjusted_stock(symbol=symbol, start_date=pd.to_datetime(start_date).strftime("%d-%m-%Y"), end_date=pd.Timestamp.today().strftime("%d-%m-%Y") if end_date is None else end_date)
            df = _normalize(raw)
            if len(df) > 50:
                return df
        except Exception:
            pass
    ticker = yf_symbol or f"{symbol}.NS"
    raw = yf.download(ticker, start=start_date, end=end_date, auto_adjust=True, progress=False)
    if raw.empty:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    raw = raw.reset_index()
    return _normalize(raw)
