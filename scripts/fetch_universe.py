from __future__ import annotations
from pathlib import Path
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'universe.csv'

# Nifty Total Market constituent sources (multiple options; use first successful)
SOURCES = [
    {
        "name": "NSE Total Market",
        "url": "https://www.nseindia.com/api/quote-equity?symbol=NIFTY%20TOTAL%20MARKET",
        "headers": {"User-Agent": "Mozilla/5.0"},
        "parse": "nse_json"
    },
    {
        "name": "Moneycontrol Nifty Mirror",
        "url": "https://m.moneycontrol.com/india/stockmarketquote/indices/nifty_total_market/stockquote",
        "parse": "html_table"
    },
    {
        "name": "NSE BhavCopy",
        "url": "https://www.nseindia.com/get-quotes/equity",
        "parse": "csv"
    }
]

def fetch_nse_json(url: str, headers: dict):
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code != 200:
        return None
    data = r.json()
    rows = []
    if "securityInfo" in data:
        info = data["securityInfo"]
        rows.append({
            "symbol": info.get("symbol", ""),
            "sector": info.get("industry", ""),
            "industry": info.get("industry", ""),
            "yf_symbol": f"{info.get('symbol', '')}.NS"
        })
    return rows if rows else None


def fetch_html_table(url: str):
    try:
        from bs4 import BeautifulSoup
        r = requests.get(url, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table")
        if not table:
            return None
        rows = []
        for tr in table.find_all("tr")[1:]:
            tds = tr.find_all("td")
            if len(tds) >= 2:
                rows.append({
                    "symbol": tds[0].get_text(strip=True),
                    "sector": tds[1].get_text(strip=True) if len(tds) > 1 else "",
                    "industry": "",
                    "yf_symbol": f"{tds[0].get_text(strip=True)}.NS"
                })
        return rows
    except Exception:
        return None


def fetch_csv(url: str):
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return None
        return pd.read_csv(r.text).to_dict("records")
    except Exception:
        return None


def main():
    existing = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame(columns=["symbol","sector","industry","yf_symbol"])
    existing_dict = {(row["symbol"], row.get("sector","")): row for _, row in existing.iterrows()}

    for src_meta in SOURCES:
        name = src_meta["name"]
        url = src_meta["url"]
        headers = src_meta.get("headers", {})
        parse = src_meta["parse"]

        rows = None
        if parse == "nse_json":
            rows = fetch_nse_json(url, headers)
        elif parse == "html_table":
            rows = fetch_html_table(url)
        elif parse == "csv":
            rows = fetch_csv(url)

        if rows and len(rows) > 10:
            merged = []
            for r in rows:
                sym = r["symbol"]
                sect = r.get("sector", "")
                key = (sym, sect)
                base = existing_dict.get(key)
                merged_row = {
                    "symbol": sym,
                    "sector": sect or (base and base.get("sector","")) or "",
                    "industry": r.get("industry","") or (base and base.get("industry","")) or "",
                    "yf_symbol": r.get("yf_symbol", f"{sym}.NS")
                }
                merged.append(merged_row)
            df_new = pd.DataFrame(merged).drop_duplicates(subset=["symbol"]).sort_values("symbol")
            df_new.to_csv(OUT, index=False)
            print(f"Fetched {len(df_new)} rows from {name} -> {OUT}")
            return

    print("No source returned valid constituents. Kept existing universe.")


if __name__ == "__main__":
    main()
