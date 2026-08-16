-- ============================================================
-- Data Validation Queries
-- Run these to verify data quality after each pipeline run
-- ============================================================


-- 1. Table Row Counts
SELECT 'portfolio_holdings' AS table_name, COUNT(*) AS row_count FROM portfolio_holdings
UNION ALL
SELECT 'daily_prices', COUNT(*) FROM daily_prices
UNION ALL
SELECT 'benchmark_prices', COUNT(*) FROM benchmark_prices
UNION ALL
SELECT 'risk_free_rate', COUNT(*) FROM risk_free_rate
UNION ALL
SELECT 'company_metadata', COUNT(*) FROM company_metadata
UNION ALL
SELECT 'computed_daily_returns', COUNT(*) FROM computed_daily_returns
UNION ALL
SELECT 'computed_portfolio_summary', COUNT(*) FROM computed_portfolio_summary
UNION ALL
SELECT 'computed_risk_metrics', COUNT(*) FROM computed_risk_metrics
UNION ALL
SELECT 'computed_sector_analysis', COUNT(*) FROM computed_sector_analysis
UNION ALL
SELECT 'computed_correlation_matrix', COUNT(*) FROM computed_correlation_matrix;


-- 2. Check for NULL adj_close (critical field)
SELECT COUNT(*) AS null_adj_close_count
FROM daily_prices
WHERE adj_close IS NULL;


-- 3. Date Range Consistency
SELECT
    'daily_prices' AS source,
    MIN(trade_date) AS min_date,
    MAX(trade_date) AS max_date,
    COUNT(DISTINCT trade_date) AS trading_days
FROM daily_prices
UNION ALL
SELECT
    'benchmark_prices',
    MIN(trade_date),
    MAX(trade_date),
    COUNT(DISTINCT trade_date)
FROM benchmark_prices
UNION ALL
SELECT
    'risk_free_rate',
    MIN(rate_date),
    MAX(rate_date),
    COUNT(DISTINCT rate_date)
FROM risk_free_rate;


-- 4. Missing Tickers (holdings without price data)
SELECT ph.ticker, 'MISSING PRICE DATA' AS issue
FROM portfolio_holdings ph
LEFT JOIN (SELECT DISTINCT ticker FROM daily_prices) dp ON ph.ticker = dp.ticker
WHERE dp.ticker IS NULL;


-- 5. Duplicate Check (should return 0 rows)
SELECT ticker, trade_date, COUNT(*) AS dupes
FROM daily_prices
GROUP BY ticker, trade_date
HAVING COUNT(*) > 1;


-- 6. Latest Prices Spot Check
SELECT
    dp.ticker,
    cm.company_name,
    dp.trade_date,
    dp.adj_close,
    dp.volume
FROM daily_prices dp
LEFT JOIN company_metadata cm ON dp.ticker = cm.ticker
WHERE dp.trade_date = (SELECT MAX(trade_date) FROM daily_prices)
ORDER BY dp.ticker;
