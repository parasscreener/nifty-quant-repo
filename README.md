# Nifty Quant Scanner

Production-ready repository for a sector-aware, rules-based Nifty Total Market stock screener and 15-year backtest pipeline inspired by public descriptions of Jim Simons / Renaissance-style quantitative trading. It uses free NSE-compatible public data access, builds a weekday scan, and emails a ranked stock table at 9:30 AM Asia/Kolkata via GitHub Actions.

## Features
- Daily weekday scan at 9:30 AM India time via GitHub Actions.
- Sector-aware stock ranking for Nifty Total Market style universes.
- Hybrid momentum + mean-reversion model.
- Regime filter using broad index and sector leadership.
- ATR-based stop loss and volatility-aware sizing.
- HTML email report and CSV attachment.
- Monthly 15-year backtest workflow.
- Config-driven parameters.

## Strategy summary
This repo implements a public-information approximation of a Renaissance-style process:
- Rules-based, systematic stock selection.
- Multiple weak edges combined into one composite score.
- Cross-sectional ranking.
- Strict risk controls.
- Sector rotation overlay.
- Out-of-sample/backtest-ready architecture.

## Repository structure
```text
.github/workflows/       GitHub Actions for scan + backtest
config/strategy.yml      Parameters and thresholds
data/universe.csv        Universe file placeholder
scripts/                 Core scanner, backtest, email, and utilities
templates/email_report.html.j2
tests/                   Lightweight tests
```

## Setup
1. Create a new GitHub repository.
2. Copy these files into the repo.
3. Add GitHub Action secrets:
   - `SMTP_HOST`
   - `SMTP_PORT`
   - `SMTP_USER`
   - `SMTP_PASS`
   - `EMAIL_TO` (optional override)
4. Edit `data/universe.csv` with your preferred Nifty Total Market universe source/constituents.
5. Trigger `workflow_dispatch` once to validate.

## Notes
- This repository uses `NSEDownload` as the primary free public NSE data wrapper.
- Because free NSE endpoints can change, a fallback to `yfinance` is included for robustness.
- For production use, validate survivorship bias, symbol history changes, corporate actions, slippage, and trading costs.


## Enhancements included
- Richer HTML email with summary cards, sector leadership table, and setup mix table.
- Output files: `screened_stocks.csv`, `sector_leadership.csv`, and `setup_mix.csv`.
- `scripts/update_universe.py` scaffold to maintain and extend the universe file before scans.

## Recommended next extension
Wire `scripts/update_universe.py` to your preferred official/public constituent source for the Nifty Total Market universe and call it as a step before the main scan workflow.
