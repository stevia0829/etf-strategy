# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chinese A-share quantitative trading strategy project ("Cibo 三驾马车" - Three Horse Carriage). Originated from [JoinQuant](https://www.joinquant.com/post/65582) community strategy, adapted for standalone use.

## Strategy Architecture

The strategy is a **portfolio of 4 independent sub-strategies**, each allocated a proportion of total capital via `g.portfolio_value_proportion = [小市值, ETF反弹, ETF轮动, 白马攻防]`:

1. **策略1 - 小市值 (Small Cap)**: Small market cap stock selection with sector diversification, stop-loss, top-divergence detection, volume-abnormality checks
2. **策略2 - ETF反弹 (ETF Bounce)**: Buys dips in CSI 2000 ETF and similar broad-market ETFs, holds for N days
3. **策略3 - ETF轮动 (ETF Rotation)**: Momentum-based rotation across 20+ ETFs (gold, oil, overseas indices, sector ETFs) with RSRS and moving-average signals
4. **策略4 - 白马攻防 (Blue Chip Defense)**: Monthly-rebalanced blue-chip strategy (experimental, author notes it underperforms)

## File Structure

- `cibo_strategy.py` (~89KB, 2000+ lines) — **Original JoinQuant platform version**. Requires `jqdata`, `jqfactor` SDKs. This is the authoritative strategy logic.
- `self_strategy.py` — Stripped-down version replacing JoinQuant APIs with mock functions + Tushare. Strategy functions are stubs (print-only).
- `cibo_strategy_standalone_fixed.py` — Standalone version using free data sources (AKShare, Baostock, Tushare). Has `DataSourceManager` for multi-source data fetching.
- `cibo_strategy_standalone_fixed_enhanced.py` — **Most complete standalone version**. Adds `Portfolio` (position tracking), `DataSourceManager` (multi-source), and `BacktestEngine` (backtesting with reporting).
- `personal_select.py` — Separate stock screener for AI-sector stocks using AKShare. Technical indicator based (MACD, RSI, divergence, volume).
- `config.json` — Tushare API token and data source priority config.

## Data Sources

Priority order: AKShare (free, recommended) > Baostock (free) > Tushare (requires token in `config.json`).

Stock codes use JoinQuant format: `000001.XSHE` (Shenzhen), `600000.XSHG` (Shanghai).

## Running

No formal build system or test framework. Scripts are run directly:

```bash
# Enhanced standalone with backtesting
python cibo_strategy_standalone_fixed_enhanced.py

# Personal stock screener (requires akshare)
python personal_select.py

# JoinQuant data SDK connection test (requires jqdatasdk)
python test_jqdata.py
```

## Key Dependencies

- `akshare`, `baostock`, `tushare` — A-share market data
- `jqdatasdk`, `jqfactor` — JoinQuant platform SDK (only for `cibo_strategy.py`)
- `pandas`, `numpy` — Data manipulation
- `prettytable` — Console table display
- `matplotlib` — Charting (enhanced standalone)

## Conventions

- All code comments and variable names are in Chinese
- Global state managed through a `g` object (class `G`) holding all strategy parameters
- Strategy scheduling uses JoinQuant-style `run_daily`/`run_weekly`/`run_monthly` with time strings like `'9:35'`
- ETF pools are hardcoded lists in `g.etf_pool_2` and `g.etf_pool_3`
- The `portfolio_value_proportion` array controls which strategies are active and their capital allocation