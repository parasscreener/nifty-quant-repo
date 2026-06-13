import pandas as pd
import numpy as np
from scripts.strategy import compute_features


def test_compute_features_smoke():
    n = 300
    df = pd.DataFrame({
        "date": pd.date_range("2020-01-01", periods=n, freq="B"),
        "open": np.linspace(100, 150, n),
        "high": np.linspace(101, 151, n),
        "low": np.linspace(99, 149, n),
        "close": np.linspace(100, 150, n),
        "volume": np.repeat(1_000_000, n),
    })
    cfg = {
        "signals": {
            "momentum_lookback_1": 60,
            "momentum_lookback_2": 120,
            "reversal_z_window": 20,
            "breakout_window": 55,
            "ma_fast": 20,
            "ma_mid": 50,
            "ma_slow": 200,
            "atr_window": 14,
            "vol_window": 20,
        }
    }
    out = compute_features(df, cfg)
    assert "ma200" in out.columns
    assert len(out) == n
