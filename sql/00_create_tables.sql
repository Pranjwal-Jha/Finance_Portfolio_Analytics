-- ============================================================
-- Financial Portfolio Analytics - Database Schema
-- Database: SQLite (portfolio.db)
-- ============================================================

-- ============================================================
-- RAW DATA TABLES (Populated by Python ingestion scripts)
-- ============================================================

-- Portfolio holdings: stocks you own
CREATE TABLE IF NOT EXISTS portfolio_holdings (
    holding_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker        TEXT NOT NULL,
    shares_held   REAL NOT NULL,
    buy_price     REAL NOT NULL,
    buy_date      TEXT NOT NULL,           -- YYYY-MM-DD
    sector        TEXT NOT NULL,
    industry      TEXT,
    UNIQUE(ticker)
);

-- Daily OHLCV price data for each stock
CREATE TABLE IF NOT EXISTS daily_prices (
    price_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker        TEXT NOT NULL,
    trade_date    TEXT NOT NULL,            -- YYYY-MM-DD
    open_price    REAL,
    high_price    REAL,
    low_price     REAL,
    close_price   REAL,
    adj_close     REAL NOT NULL,
    volume        INTEGER,
    UNIQUE(ticker, trade_date)
);

-- S&P 500 benchmark daily prices
CREATE TABLE IF NOT EXISTS benchmark_prices (
    bench_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date    TEXT NOT NULL,            -- YYYY-MM-DD
    close_price   REAL NOT NULL,
    UNIQUE(trade_date)
);

-- US 10-Year Treasury yield (risk-free rate)
CREATE TABLE IF NOT EXISTS risk_free_rate (
    rate_date     TEXT PRIMARY KEY,         -- YYYY-MM-DD
    yield_pct     REAL NOT NULL             -- Annual yield as percentage
);

-- Company metadata (static info)
CREATE TABLE IF NOT EXISTS company_metadata (
    ticker        TEXT PRIMARY KEY,
    company_name  TEXT,
    sector        TEXT,
    industry      TEXT,
    market_cap    REAL,
    last_updated  TEXT                      -- YYYY-MM-DD
);


-- ============================================================
-- COMPUTED TABLES (Populated by Python analytics engine)
-- ============================================================

-- Daily returns per stock
CREATE TABLE IF NOT EXISTS computed_daily_returns (
    ticker            TEXT NOT NULL,
    trade_date        TEXT NOT NULL,
    daily_return      REAL,
    cumulative_return REAL,
    UNIQUE(ticker, trade_date)
);

-- Risk metrics (per stock + portfolio level)
CREATE TABLE IF NOT EXISTS computed_risk_metrics (
    ticker          TEXT NOT NULL,          -- 'PORTFOLIO' for portfolio-level
    metric_name     TEXT NOT NULL,
    metric_value    REAL,
    as_of_date      TEXT NOT NULL,
    lookback_period TEXT NOT NULL,          -- '1Y', '3Y', 'ALL'
    UNIQUE(ticker, metric_name, lookback_period)
);

-- Sector analysis
CREATE TABLE IF NOT EXISTS computed_sector_analysis (
    sector              TEXT NOT NULL,
    total_market_value  REAL,
    portfolio_weight    REAL,
    sector_return       REAL,
    as_of_date          TEXT NOT NULL,
    UNIQUE(sector, as_of_date)
);

-- Daily portfolio summary
CREATE TABLE IF NOT EXISTS computed_portfolio_summary (
    trade_date            TEXT PRIMARY KEY,
    total_portfolio_value REAL,
    daily_return          REAL,
    cumulative_return     REAL,
    drawdown              REAL
);

-- Pairwise correlation matrix
CREATE TABLE IF NOT EXISTS computed_correlation_matrix (
    ticker_1        TEXT NOT NULL,
    ticker_2        TEXT NOT NULL,
    correlation     REAL,
    lookback_period TEXT NOT NULL,
    UNIQUE(ticker_1, ticker_2, lookback_period)
);


-- ============================================================
-- INDEXES (Performance optimization for queries & Tableau)
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_daily_prices_ticker_date
    ON daily_prices(ticker, trade_date);

CREATE INDEX IF NOT EXISTS idx_daily_prices_date
    ON daily_prices(trade_date);

CREATE INDEX IF NOT EXISTS idx_benchmark_date
    ON benchmark_prices(trade_date);

CREATE INDEX IF NOT EXISTS idx_returns_ticker_date
    ON computed_daily_returns(ticker, trade_date);

CREATE INDEX IF NOT EXISTS idx_risk_metrics_ticker
    ON computed_risk_metrics(ticker, metric_name);

CREATE INDEX IF NOT EXISTS idx_portfolio_summary_date
    ON computed_portfolio_summary(trade_date);
