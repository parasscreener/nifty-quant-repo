from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'universe.csv'

# Starter auto-updater scaffold.
# Replace source URLs/parsers as needed when you settle on a preferred official/public constituent source.
# For now, it preserves existing rows and can be extended to fetch NSE constituent files.

def main():
    df = pd.read_csv(OUT)
    df = df.drop_duplicates(subset=['symbol']).sort_values('symbol')
    df.to_csv(OUT, index=False)
    print(f'Universe rows: {len(df)} written to {OUT}')

if __name__ == '__main__':
    main()
