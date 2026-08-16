# Data Dictionary

This document defines every column used across all tables in the `portfolio.db` SQLite database.

---

## Table: `portfolio_holdings`

Defines the stocks you own, their quantities, and purchase details.

| Column | Type | Description |
|---|---|---|
| `holding_id` | INTEGER (PK) | Auto-incremented unique identifier |
| `ticker` | TEXT | Stock ticker symbol (e.g., AAPL, MSFT) |
| `shares_held` | REAL | Number of shares currently held |
| `buy_price` | REAL | Average purchase price per share (USD) |
| `buy_date` | TEXT (DATE) | Date of purchase (YYYY-MM-DD) |
| `sector` | TEXT | GICS sector classification |
| `industry` | TEXT | Industry sub-classification |

---

## Table: `daily_prices`

Historical daily OHLCV price data for each stock in the portfolio.

| Column | Type | Description |
|---|---|---|
| `price_id` | INTEGER (PK) | Auto-incremented unique identifier |
| `ticker` | TEXT | Stock ticker symbol |
| `trade_date` | TEXT (DATE) | Trading date (YYYY-MM-DD) |
| `open_price` | REAL | Opening price for the day |
| `high_price` | REAL | Highest price during the day |
| `low_price` | REAL | Lowest price during the day |
| `close_price` | REAL | Closing price for the day |
| `adj_close` | REAL | Adjusted closing price (accounts for splits & dividends) |
| `volume` | INTEGER | Number of shares traded |

> **Note**: `adj_close` is the primary price used for return calculations. It accounts for corporate actions like stock splits and dividend distributions.

---

## Table: `benchmark_prices`

Daily closing prices for the S&P 500 index (^GSPC), used as the market benchmark.

| Column | Type | Description |
|---|---|---|
| `bench_id` | INTEGER (PK) | Auto-incremented unique identifier |
| `trade_date` | TEXT (DATE) | Trading date (YYYY-MM-DD) |
| `close_price` | REAL | S&P 500 closing price |

---

## Table: `risk_free_rate`

Daily US 10-Year Treasury yield (^TNX), used as the risk-free rate in Sharpe/Sortino/CAPM calculations.

| Column | Type | Description |
|---|---|---|
| `rate_date` | TEXT (DATE, PK) | Date (YYYY-MM-DD) |
| `yield_pct` | REAL | Annual yield in percentage (e.g., 4.25 = 4.25%) |

---

## Table: `company_metadata`

Static information about each company in the portfolio.

| Column | Type | Description |
|---|---|---|
| `ticker` | TEXT (PK) | Stock ticker symbol |
| `company_name` | TEXT | Full company name |
| `sector` | TEXT | GICS sector |
| `industry` | TEXT | Industry classification |
| `market_cap` | REAL | Market capitalization in USD |
| `last_updated` | TEXT (DATE) | Date when metadata was last refreshed |

---

## Computed Tables

These tables are populated by Python analytics scripts (Phase 3).

### Table: `computed_daily_returns`

| Column | Type | Description |
|---|---|---|
| `ticker` | TEXT | Stock ticker symbol |
| `trade_date` | TEXT (DATE) | Trading date |
| `daily_return` | REAL | Daily percentage return: (P₁ - P₀) / P₀ |
| `cumulative_return` | REAL | Cumulative return since first date in dataset |

### Table: `computed_risk_metrics`

| Column | Type | Description |
|---|---|---|
| `ticker` | TEXT | Stock ticker (or 'PORTFOLIO' for portfolio-level) |
| `metric_name` | TEXT | Name of the metric (e.g., 'sharpe_ratio', 'var_95') |
| `metric_value` | REAL | Computed value of the metric |
| `as_of_date` | TEXT (DATE) | Date the metric was computed |
| `lookback_period` | TEXT | Period used (e.g., '1Y', '3Y', 'ALL') |

### Table: `computed_sector_analysis`

| Column | Type | Description |
|---|---|---|
| `sector` | TEXT | Sector name |
| `total_market_value` | REAL | Total market value of holdings in this sector |
| `portfolio_weight` | REAL | Percentage weight in portfolio |
| `sector_return` | REAL | Weighted return of the sector |
| `as_of_date` | TEXT (DATE) | Date of computation |

### Table: `computed_portfolio_summary`

| Column | Type | Description |
|---|---|---|
| `trade_date` | TEXT (DATE) | Trading date |
| `total_portfolio_value` | REAL | Sum of all holdings' market values |
| `daily_return` | REAL | Portfolio-level daily return |
| `cumulative_return` | REAL | Portfolio-level cumulative return |
| `drawdown` | REAL | Current drawdown from peak |

### Table: `computed_correlation_matrix`

| Column | Type | Description |
|---|---|---|
| `ticker_1` | TEXT | First stock in the pair |
| `ticker_2` | TEXT | Second stock in the pair |
| `correlation` | REAL | Pearson correlation coefficient (-1 to +1) |
| `lookback_period` | TEXT | Period used for calculation |
