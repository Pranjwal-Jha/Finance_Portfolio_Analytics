# Financial Portfolio Risk and Market Analytics Platform

A quantitative portfolio analytics and risk measurement engine designed to track multi-asset equity portfolios, evaluate risk-adjusted performance, and deliver institutional-grade business intelligence. Built with Python, SQLite, SQL analytical views, and Tableau.

---

## Overview

The Financial Portfolio Risk and Market Analytics Platform provides an end-to-end data and analytics pipeline for multi-sector equity portfolios. The platform automates data ingestion from financial markets, normalizes historical time-series data in a relational data warehouse, calculates key risk-adjusted performance metrics, and exposes pre-aggregated views for interactive dashboard reporting.

### Primary Objectives
- **Automated Data Engineering**: Streamline extraction and transformation of multi-year adjusted daily price series for equity assets, market benchmarks (S&P 500), and risk-free yield curves (US 10-Year Treasury).
- **Institutional Risk Modeling**: Quantify portfolio tail risk and market sensitivity using historical Value at Risk (VaR), Conditional Value at Risk (CVaR / Expected Shortfall), Maximum Drawdown, Beta, Jensen's Alpha, Sharpe Ratio, Sortino Ratio, and the Herfindahl-Hirschman Index (HHI).
- **Relational Analytics Layer**: Maintain optimized SQLite tables and analytical SQL views leveraging Common Table Expressions (CTEs) and window functions for fast query execution and BI interoperability.
- **Decision Intelligence**: Deliver interactive visual analytics for asset allocation, sector exposure, risk attribution, and benchmark comparison.

---

## Architecture and Data Flow

```
[Market Data Providers]
   - Yahoo Finance (yfinance)
   - Benchmark Index (^GSPC)
   - US 10-Year Treasury Yield (^TNX)
              │
              ▼
[Python ETL Pipeline]
   - 01_fetch_data.py
   - 02_load_to_sqlite.py
              │
              ▼
[SQLite Data Warehouse] (data/portfolio.db)
   - portfolio_holdings
   - daily_prices
   - benchmark_prices
   - risk_free_rate
   - company_metadata
              │
              ▼
[Analytics & Quantitative Modeling]
   - 03_compute_analytics.py
   - 05_create_sql_views.py
              │
              ▼
[Consumption Layer]
   - SQL Analytical Views (vw_*)
   - Tableau Workbook (tableau/portfoio_Analytics.twbx)
   - Interactive Web Dashboard (index.html / dashboard.html)
```

---

## Key Features

- **Multi-Sector Equity Universe**: Tracks an 18-asset diversified portfolio across 6 primary sectors: Technology, Healthcare, Financials, Consumer, Energy, and Industrials.
- **Comprehensive Risk Suite**: Computes volatility, downside deviation, historical VaR (95%), CVaR (Expected Shortfall), Maximum Drawdown, Beta, Jensen's Alpha, Tracking Error, Information Ratio, and portfolio concentration (HHI).
- **Modular Pipeline Architecture**: Decoupled Python scripts for fetching market data, database normalization, statistical computation, and view generation.
- **SQL-First Analytics**: Pre-computed views with analytical window functions and joins optimized for direct connection to Tableau, Power BI, or web frontends.
- **Interactive Visual Reporting**: Includes packaged Tableau workbooks and standalone interactive web dashboards.

---

## Project Structure

```
Financial_Portfolio_Analytics/
├── README.md                        # Project documentation
├── requirements.txt                 # Python dependencies
├── portfolio_config.csv             # Portfolio configuration (tickers, shares, purchase prices)
├── index.html                       # Standalone interactive dashboard interface
├── dashboard.html                   # HTML dashboard visualization asset
├── data/
│   ├── portfolio.db                 # Central SQLite database
│   └── backups/                     # Raw and backup CSV exports
├── docs/
│   ├── data_dictionary.md           # Database schema and column specifications
│   └── methodology.md               # Mathematical definitions and statistical methodology
├── scripts/
│   ├── 01_fetch_data.py             # Extracts historical market data via yfinance
│   ├── 02_load_to_sqlite.py         # Transforms and loads market data into SQLite tables
│   ├── 03_compute_analytics.py      # Computes returns, risk metrics, and correlations
│   ├── 04_generate_dashboard.py     # Generates interactive dashboard reports
│   ├── 05_create_sql_views.py       # Builds Tableau-ready SQL views in the database
│   └── 06_run_pipeline.py           # Master execution script for the end-to-end pipeline
├── sql/
│   ├── 00_create_tables.sql         # Schema definition DDL
│   ├── 01_analytical_queries.sql    # Analytical SQL queries for performance reporting
│   ├── 02_tableau_views.sql         # View definitions for BI tools
│   └── 03_validation_queries.sql    # Data integrity and validation queries
└── tableau/
    ├── portfoio_Analytics.twbx      # Packaged Tableau workbook
    └── csv_exports/                 # Exported datasets for BI integration
```

---

## Portfolio Universe

| Sector | Tickers | Target Allocation |
|---|---|---|
| Technology | AAPL, MSFT, GOOGL, NVDA | ~30% |
| Healthcare | JNJ, UNH, PFE | ~12% |
| Financials | JPM, GS, V, BRK-B | ~18% |
| Consumer | AMZN, PG, KO | ~15% |
| Energy | XOM, CVX | ~12% |
| Industrials | CAT, HON | ~8% |

---

## Quantitative Metrics and Risk Methodology

| Metric | Formulation / Methodology | Financial Interpretation |
|---|---|---|
| **Daily Return** | $r_t = (P_t - P_{t-1}) / P_{t-1}$ | Period-over-period percentage price movement using adjusted closing prices. |
| **Annualized Volatility** | $\sigma_{ann} = \sigma_{daily} \times \sqrt{252}$ | Standard deviation of daily returns scaled to an annual basis. |
| **Sharpe Ratio** | $(R_{ann} - R_f) / \sigma_{ann}$ | Excess return generated per unit of total risk (benchmark: US 10-Year Treasury). |
| **Sortino Ratio** | $(R_{ann} - R_f) / \sigma_{downside}$ | Excess return evaluated strictly against downside risk / negative volatility. |
| **Value at Risk (VaR 95%)** | 5th percentile of historical return distribution | Maximum expected loss over a 1-day horizon at a 95% confidence level. |
| **Conditional VaR (CVaR)** | $\mathbb{E}[r \mid r \le \text{VaR}_{0.95}]$ | Expected loss on trading days when losses breach the 95% VaR threshold. |
| **Maximum Drawdown (MDD)** | $\min_t ((P_t - P_{peak,t}) / P_{peak,t})$ | Maximum observed peak-to-trough decline over the investment horizon. |
| **Beta ($\beta$)** | $\text{Cov}(r_i, r_m) / \text{Var}(r_m)$ | Systematic market risk relative to the S&P 500 index. |
| **Jensen's Alpha ($\alpha$)** | $R_p - [R_f + \beta (R_m - R_f)]$ | Portfolio excess return generated beyond Capital Asset Pricing Model (CAPM) expectations. |
| **Tracking Error** | $\sigma(r_p - r_b)$ | Standard deviation of excess returns relative to the benchmark. |
| **Information Ratio** | $(R_p - R_b) / \text{Tracking Error}$ | Active return relative to active risk. |
| **Herfindahl-Hirschman Index** | $\sum w_i^2$ | Concentration metric evaluating asset weight distribution across holdings. |

For detailed mathematical formulations, refer to the [Methodology Documentation](docs/methodology.md).

---

## Installation and Quickstart

### Prerequisites
- Python 3.8 or higher
- SQLite 3
- Tableau Desktop or Tableau Public (optional, for viewing `.twbx` files)

### 1. Clone the Repository
```bash
git clone https://github.com/Pranjwal-Jha/Finance_Portfolio_Analytics.git
cd Finance_Portfolio_Analytics
```

### 2. Configure Environment and Dependencies
Create and activate a virtual environment, then install required Python packages:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the Master Analytics Pipeline
Execute the automated end-to-end workflow:

```bash
python scripts/06_run_pipeline.py
```

This single command executes:
1. `01_fetch_data.py`: Downloads latest OHLCV data for all portfolio assets, S&P 500, and Treasury yields.
2. `02_load_to_sqlite.py`: Initializes schema and populates SQLite tables.
3. `03_compute_analytics.py`: Calculates returns, risk metrics, drawdowns, and correlation matrices.
4. `04_generate_dashboard.py`: Exports updated metrics for visual dashboards.
5. `05_create_sql_views.py`: Builds analytical views (`vw_*`) in the database.

---

## Database Architecture and SQL Views

The database schema is documented in detail in the [Data Dictionary](docs/data_dictionary.md).

### Core Tables
- `portfolio_holdings`: Asset quantities, purchase price, and sector classification.
- `daily_prices`: Historical daily OHLCV and adjusted closing prices.
- `benchmark_prices`: Historical daily prices for the S&P 500 (^GSPC).
- `risk_free_rate`: Daily US 10-Year Treasury yields (^TNX).
- `company_metadata`: Descriptive metadata, market capitalization, and sector hierarchy.

### Analytical SQL Views
The pipeline exposes several pre-computed analytical views in `portfolio.db`:
- `vw_portfolio_summary`: Daily total portfolio market value, daily return, and cumulative return.
- `vw_sector_allocation`: Current sector weights, market value distribution, and sector-level performance.
- `vw_risk_metrics`: Summary table of Sharpe, Sortino, VaR, CVaR, Beta, Alpha, and Drawdowns across assets.
- `vw_stock_performance`: Asset-level return metrics, current price, unrealized gain/loss, and holding weight.

---

## Connecting BI Tools (Tableau / Power BI)

1. Open Tableau Desktop / Tableau Public.
2. Select **Connect to Data** -> **SQLite** (or use the exported CSV files in `tableau/csv_exports/`).
3. Select `data/portfolio.db`.
4. Drag and drop the desired analytical views (`vw_portfolio_summary`, `vw_risk_metrics`, etc.) to create custom dashboards, or open the pre-built workbook at `tableau/portfoio_Analytics.twbx`.

---

## Documentation Links

- [Data Dictionary](docs/data_dictionary.md) - Column specifications, data types, and entity relationships.
- [Methodology & Formulas](docs/methodology.md) - Mathematical definitions and calculation standards.

---

## License and Disclaimer

This project is licensed for educational, research, and portfolio demonstration purposes. Financial analytics and risk metrics generated by this software do not constitute formal investment advice.
