-- ============================================================
-- Standalone SQL Analytical Queries
-- These demonstrate advanced SQL skills independently of Python
-- ============================================================


-- ─────────────────────────────────────────────
-- 1. Top 5 Stocks by Risk-Adjusted Return (Sharpe Ratio)
-- ─────────────────────────────────────────────
SELECT
    rm.ticker,
    cm.company_name,
    ph.sector,
    ROUND(MAX(CASE WHEN rm.metric_name = 'sharpe_ratio' THEN rm.metric_value END), 4) AS sharpe_ratio,
    ROUND(MAX(CASE WHEN rm.metric_name = 'annualized_return' THEN rm.metric_value END) * 100, 2) AS ann_return_pct,
    ROUND(MAX(CASE WHEN rm.metric_name = 'annualized_volatility' THEN rm.metric_value END) * 100, 2) AS ann_vol_pct
FROM computed_risk_metrics rm
LEFT JOIN company_metadata cm ON rm.ticker = cm.ticker
LEFT JOIN portfolio_holdings ph ON rm.ticker = ph.ticker
WHERE rm.lookback_period = 'ALL'
  AND rm.ticker != 'PORTFOLIO'
GROUP BY rm.ticker
ORDER BY sharpe_ratio DESC
LIMIT 5;


-- ─────────────────────────────────────────────
-- 2. Stocks with Drawdown Exceeding 20%
-- ─────────────────────────────────────────────
SELECT
    rm.ticker,
    cm.company_name,
    ROUND(rm.metric_value * 100, 2) AS max_drawdown_pct,
    ROUND(ret.metric_value * 100, 2) AS total_return_pct,
    CASE
        WHEN rm.metric_value < -0.30 THEN 'SEVERE (>30%)'
        WHEN rm.metric_value < -0.20 THEN 'SIGNIFICANT (>20%)'
        ELSE 'MODERATE'
    END AS drawdown_severity
FROM computed_risk_metrics rm
LEFT JOIN company_metadata cm ON rm.ticker = cm.ticker
LEFT JOIN computed_risk_metrics ret
    ON rm.ticker = ret.ticker
    AND ret.metric_name = 'total_return'
    AND ret.lookback_period = rm.lookback_period
WHERE rm.metric_name = 'max_drawdown'
  AND rm.lookback_period = 'ALL'
  AND rm.metric_value < -0.20
  AND rm.ticker != 'PORTFOLIO'
ORDER BY rm.metric_value ASC;


-- ─────────────────────────────────────────────
-- 3. Days Where Portfolio Loss Exceeded VaR
-- ─────────────────────────────────────────────
WITH portfolio_var AS (
    SELECT metric_value AS var_threshold
    FROM computed_risk_metrics
    WHERE ticker = 'PORTFOLIO'
      AND metric_name = 'var_95'
      AND lookback_period = 'ALL'
)
SELECT
    ps.trade_date,
    ROUND(ps.daily_return * 100, 4) AS daily_loss_pct,
    ROUND(pv.var_threshold * 100, 4) AS var_threshold_pct,
    ROUND(ps.total_portfolio_value, 2) AS portfolio_value,
    ROUND(ps.drawdown * 100, 4) AS drawdown_pct
FROM computed_portfolio_summary ps
CROSS JOIN portfolio_var pv
WHERE ps.daily_return < pv.var_threshold
ORDER BY ps.daily_return ASC
LIMIT 20;


-- ─────────────────────────────────────────────
-- 4. Best Performing Sector Per Quarter
-- ─────────────────────────────────────────────
WITH quarterly_sector_returns AS (
    SELECT
        ph.sector,
        SUBSTR(dp.trade_date, 1, 4) AS year,
        CASE
            WHEN CAST(SUBSTR(dp.trade_date, 6, 2) AS INTEGER) <= 3 THEN 'Q1'
            WHEN CAST(SUBSTR(dp.trade_date, 6, 2) AS INTEGER) <= 6 THEN 'Q2'
            WHEN CAST(SUBSTR(dp.trade_date, 6, 2) AS INTEGER) <= 9 THEN 'Q3'
            ELSE 'Q4'
        END AS quarter,
        AVG(cr.daily_return) * 252 AS annualized_sector_return
    FROM daily_prices dp
    INNER JOIN portfolio_holdings ph ON dp.ticker = ph.ticker
    INNER JOIN computed_daily_returns cr ON dp.ticker = cr.ticker AND dp.trade_date = cr.trade_date
    GROUP BY ph.sector, year, quarter
),
ranked_sectors AS (
    SELECT
        *,
        RANK() OVER (
            PARTITION BY year, quarter
            ORDER BY annualized_sector_return DESC
        ) AS sector_rank
    FROM quarterly_sector_returns
)
SELECT
    year || '-' || quarter AS period,
    sector AS best_sector,
    ROUND(annualized_sector_return * 100, 2) AS ann_return_pct
FROM ranked_sectors
WHERE sector_rank = 1
ORDER BY year, quarter;


-- ─────────────────────────────────────────────
-- 5. Year-over-Year Return Comparison
-- ─────────────────────────────────────────────
WITH yearly_returns AS (
    SELECT
        SUBSTR(trade_date, 1, 4) AS year,
        (LAST_VALUE(total_portfolio_value) OVER (
            PARTITION BY SUBSTR(trade_date, 1, 4)
            ORDER BY trade_date
            RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) / FIRST_VALUE(total_portfolio_value) OVER (
            PARTITION BY SUBSTR(trade_date, 1, 4)
            ORDER BY trade_date
        ) - 1) AS yearly_return,
        trade_date
    FROM computed_portfolio_summary
)
SELECT DISTINCT
    year,
    ROUND(yearly_return * 100, 2) AS return_pct,
    CASE
        WHEN yearly_return > 0.20 THEN 'EXCELLENT'
        WHEN yearly_return > 0.10 THEN 'GOOD'
        WHEN yearly_return > 0.00 THEN 'POSITIVE'
        ELSE 'NEGATIVE'
    END AS performance_category
FROM yearly_returns
ORDER BY year;


-- ─────────────────────────────────────────────
-- 6. Portfolio Allocation vs Equal-Weight Comparison
-- ─────────────────────────────────────────────
SELECT
    ph.ticker,
    cm.company_name,
    ph.sector,
    ROUND((ph.shares_held * dp.adj_close) /
        (SELECT SUM(ph2.shares_held * dp2.adj_close)
         FROM portfolio_holdings ph2
         INNER JOIN daily_prices dp2 ON ph2.ticker = dp2.ticker
         WHERE dp2.trade_date = (SELECT MAX(trade_date) FROM daily_prices)
        ) * 100, 2) AS actual_weight_pct,
    ROUND(100.0 / (SELECT COUNT(*) FROM portfolio_holdings), 2) AS equal_weight_pct,
    ROUND(
        (ph.shares_held * dp.adj_close) /
        (SELECT SUM(ph2.shares_held * dp2.adj_close)
         FROM portfolio_holdings ph2
         INNER JOIN daily_prices dp2 ON ph2.ticker = dp2.ticker
         WHERE dp2.trade_date = (SELECT MAX(trade_date) FROM daily_prices)
        ) * 100 - 100.0 / (SELECT COUNT(*) FROM portfolio_holdings),
    2) AS overweight_pct
FROM portfolio_holdings ph
INNER JOIN daily_prices dp ON ph.ticker = dp.ticker
LEFT JOIN company_metadata cm ON ph.ticker = cm.ticker
WHERE dp.trade_date = (SELECT MAX(trade_date) FROM daily_prices)
ORDER BY actual_weight_pct DESC;


-- ─────────────────────────────────────────────
-- 7. Highly Correlated Stock Pairs (Diversification Risk)
-- ─────────────────────────────────────────────
SELECT
    cm.ticker_1,
    cm.ticker_2,
    ROUND(cm.correlation, 4) AS correlation,
    ph1.sector AS sector_1,
    ph2.sector AS sector_2,
    CASE
        WHEN ph1.sector = ph2.sector THEN 'Same Sector'
        ELSE 'Cross Sector'
    END AS pair_type
FROM computed_correlation_matrix cm
LEFT JOIN portfolio_holdings ph1 ON cm.ticker_1 = ph1.ticker
LEFT JOIN portfolio_holdings ph2 ON cm.ticker_2 = ph2.ticker
WHERE cm.ticker_1 != cm.ticker_2
  AND cm.correlation > 0.7
ORDER BY cm.correlation DESC;


-- ─────────────────────────────────────────────
-- 8. Risk vs Return Scatter Data (for Tableau scatter plot)
-- ─────────────────────────────────────────────
SELECT
    rm_ret.ticker,
    COALESCE(cm.company_name, rm_ret.ticker) AS company_name,
    ph.sector,
    ROUND(rm_ret.metric_value * 100, 2) AS total_return_pct,
    ROUND(rm_vol.metric_value * 100, 2) AS annualized_vol_pct,
    ROUND(rm_sharpe.metric_value, 4) AS sharpe_ratio,
    ROUND(rm_beta.metric_value, 4) AS beta
FROM computed_risk_metrics rm_ret
LEFT JOIN computed_risk_metrics rm_vol
    ON rm_ret.ticker = rm_vol.ticker
    AND rm_vol.metric_name = 'annualized_volatility'
    AND rm_vol.lookback_period = rm_ret.lookback_period
LEFT JOIN computed_risk_metrics rm_sharpe
    ON rm_ret.ticker = rm_sharpe.ticker
    AND rm_sharpe.metric_name = 'sharpe_ratio'
    AND rm_sharpe.lookback_period = rm_ret.lookback_period
LEFT JOIN computed_risk_metrics rm_beta
    ON rm_ret.ticker = rm_beta.ticker
    AND rm_beta.metric_name = 'beta'
    AND rm_beta.lookback_period = rm_ret.lookback_period
LEFT JOIN company_metadata cm ON rm_ret.ticker = cm.ticker
LEFT JOIN portfolio_holdings ph ON rm_ret.ticker = ph.ticker
WHERE rm_ret.metric_name = 'total_return'
  AND rm_ret.lookback_period = 'ALL'
  AND rm_ret.ticker != 'PORTFOLIO'
ORDER BY total_return_pct DESC;
