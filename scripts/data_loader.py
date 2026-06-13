from __future__ import annotations
import warnings
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

try:
    from NSEDownload import stocks
except Exception:
    stocks = None


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        flat = []
        for col in df.columns:
            parts = [str(x).strip() for x in col if x is not None and str(x).strip() and str(x).lower() != 'nan']
            flat.append('_'.join(parts))
        df.columns = flat
    else:
        df.columns = [str(c).strip() if not isinstance(c, tuple) else '_'.join([str(x).strip() for x in c if x is not None and str(x).strip()]) for c in df.columns]
    return df


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = _flatten_columns(df)
    rename_map = {}
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl in ['date', 'datetime']:
            rename_map[c] = 'date'
        elif cl.startswith('open'):
            rename_map[c] = 'open'
        elif cl.startswith('high'):
            rename_map[c] = 'high'
        elif cl.startswith('low'):
            rename_map[c] = 'low'
        elif cl in ['close', 'adj close', 'adj_close'] or cl.startswith('close'):
            rename_map[c] = 'close'
        elif cl in ['volume', 'shares traded', 'shares_traded'] or cl.startswith('volume'):
            rename_map[c] = 'volume'
    df = df.rename(columns=rename_map)

    if 'date' not in df.columns:
        idx_name = df.index.name or 'index'
        df = df.reset_index().rename(columns={idx_name: 'date'})
        if 'date' not in df.columns and 'Date' in df.columns:
            df = df.rename(columns={'Date': 'date'})

    needed = ['date', 'open', 'high', 'low', 'close', 'volume']
    missing = [c for c in ['date', 'open', 'high', 'low', 'close'] if c not in df.columns]
    if missing:
        return pd.DataFrame(columns=needed)

    if 'volume' not in df.columns:
        df['volume'] = 0

    df = df[[c for c in needed if c in df.columns]].copy()
    df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.tz_localize(None)
    df = df.dropna(subset=['date', 'open', 'high', 'low', 'close'])
    return df.sort_values('date').drop_duplicates('date')


def fetch_symbol_history(symbol: str, yf_symbol: str | None, start_date: str, end_date: str | None):
    if stocks is not None:
        try:
            raw = stocks.get_adjusted_stock(
                symbol=symbol,
                start_date=pd.to_datetime(start_date).strftime('%d-%m-%Y'),
                end_date=pd.Timestamp.today().strftime('%d-%m-%Y') if end_date is None else pd.to_datetime(end_date).strftime('%d-%m-%Y')
            )
            df = _normalize(raw)
            if len(df) > 50:
                return df
        except Exception:
            pass

    ticker = yf_symbol or f'{symbol}.NS'
    raw = yf.download(ticker, start=start_date, end=end_date, auto_adjust=True, progress=False)
    if raw.empty:
        return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    raw = raw.reset_index()
    return _normalize(raw)
