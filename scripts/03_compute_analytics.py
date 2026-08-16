"""
03_compute_analytics.py — Core Analytics Engine

Computes all financial metrics using Python (pandas, numpy, scipy):
    1. Daily & cumulative returns per stock
    2. Weighted portfolio returns & portfolio summary
    3. Risk metrics: Volatility, Sharpe, Sortino, VaR, CVaR, Max Drawdown
    4. CAPM metrics: Alpha, Beta, Tracking Error, Information Ratio
    5. Sector analysis & allocation
    6. Correlation matrix
    7. Rolling metrics (30/60/90-day)

All computed results are written back to the SQLite database.
"""

import os
import sqlite3
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime
from dotenv import load_dotenv

# Configuration

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, os.getenv("DB_PATH", "data/portfolio.db"))

# Constants
TRADING_DAYS_PER_YEAR = 252
LOOKBACK_PERIODS = {
    "1Y": 252,
    "3Y": 756,
    "ALL": None,  # Use all available data
}
ROLLING_WINDOWS = [30, 60, 90]


def load_data_from_db():
    """Load all required data from SQLite database."""
    print("\n Loading data from database...")

    conn = sqlite3.connect(DB_PATH)

    # Load stock prices
    df_prices = pd.read_sql("""
        SELECT ticker, trade_date, adj_close, close_price, volume
        FROM daily_prices
        ORDER BY ticker, trade_date
    """, conn)
    df_prices["trade_date"] = pd.to_datetime(df_prices["trade_date"])

    # Load portfolio holdings
    df_holdings = pd.read_sql("SELECT * FROM portfolio_holdings", conn)

    # Load benchmark prices
    df_benchmark = pd.read_sql("""
        SELECT trade_date, close_price as benchmark_close
        FROM benchmark_prices
        ORDER BY trade_date
    """, conn)
    df_benchmark["trade_date"] = pd.to_datetime(df_benchmark["trade_date"])

    # Load risk-free rate
    df_rf = pd.read_sql("""
        SELECT rate_date as trade_date, yield_pct
        FROM risk_free_rate
        ORDER BY rate_date
    """, conn)
    df_rf["trade_date"] = pd.to_datetime(df_rf["trade_date"])

    conn.close()

    print(f"  Prices:    {len(df_prices):,} rows ({df_prices['ticker'].nunique()} stocks)")
    print(f"  Holdings:  {len(df_holdings)} stocks")
    print(f"  Benchmark: {len(df_benchmark):,} rows")
    print(f"  Risk-free: {len(df_rf):,} rows")

    return df_prices, df_holdings, df_benchmark, df_rf


# 1. RETURN CALCULATIONS

def compute_stock_returns(df_prices):
    """
    Compute daily and cumulative returns for each stock.
    
    Daily Return:      r_t = (P_t - P_{t-1}) / P_{t-1}
    Cumulative Return: R = product(1 + r_i) - 1
    """
    print("\n Computing stock returns...")

    # Pivot to wide format for easier computation
    price_pivot = df_prices.pivot(
        index="trade_date", columns="ticker", values="adj_close"
    )

    daily_returns = price_pivot.pct_change()

    cumulative_returns = (1 + daily_returns).cumprod() - 1

    records = []
    for ticker in daily_returns.columns:
        for date in daily_returns.index:
            dr = daily_returns.loc[date, ticker]
            cr = cumulative_returns.loc[date, ticker]
            if pd.notna(dr):
                records.append({
                    "ticker": ticker,
                    "trade_date": date.strftime("%Y-%m-%d"),
                    "daily_return": round(float(dr), 8),
                    "cumulative_return": round(float(cr), 8),
                })

    df_returns = pd.DataFrame(records)

    print(f" Computed returns for {daily_returns.columns.nunique()} stocks")
    print(f" Total return records: {len(df_returns):,}")

    return df_returns, daily_returns, cumulative_returns, price_pivot


def compute_portfolio_returns(daily_returns, price_pivot, df_holdings):
    """
    Compute portfolio-level daily returns using market-value weights.
    
    Portfolio Return: R_p = sum(w_i * r_i)
    where w_i = (shares_i * price_i) / total_portfolio_value
    """
    print("\n Computing portfolio returns...")

    shares = df_holdings.set_index("ticker")["shares_held"]

    common_tickers = list(set(shares.index) & set(price_pivot.columns))
    shares = shares[common_tickers]
    prices = price_pivot[common_tickers]
    returns = daily_returns[common_tickers]

    market_values = prices.multiply(shares)

    total_value = market_values.sum(axis=1)

    weights = market_values.div(total_value, axis=0)
    portfolio_daily_return = (weights.shift(1) * returns).sum(axis=1)

    portfolio_cumulative = (1 + portfolio_daily_return).cumprod() - 1

    running_max = (1 + portfolio_cumulative).cummax()
    drawdown = (1 + portfolio_cumulative) / running_max - 1

    df_portfolio = pd.DataFrame({
        "trade_date": total_value.index.strftime("%Y-%m-%d"),
        "total_portfolio_value": total_value.round(2).values,
        "daily_return": portfolio_daily_return.round(8).values,
        "cumulative_return": portfolio_cumulative.round(8).values,
        "drawdown": drawdown.round(8).values,
    }).dropna()

    print(f"  Portfolio summary: {len(df_portfolio):,} days")
    print(f"  Latest portfolio value: ${total_value.iloc[-1]:,.2f}")
    print(f"  Total cumulative return: {portfolio_cumulative.iloc[-1]:.2%}")
    print(f"  Max drawdown: {drawdown.min():.2%}")

    return df_portfolio, portfolio_daily_return, weights, total_value


# 2. RISK METRICS

def compute_risk_metrics(daily_returns, portfolio_daily_return, df_benchmark, df_rf):
    """
    Compute risk metrics for each stock and the portfolio.
    
    Metrics:
        - Annualized Return & Volatility
        - Sharpe Ratio
        - Sortino Ratio
        - Value at Risk (VaR) at 95%
        - Conditional VaR (CVaR / Expected Shortfall)
        - Max Drawdown
        - Beta (vs S&P 500)
        - Alpha (Jensen's, CAPM-based)
        - Tracking Error
        - Information Ratio
    """
    print("\n Computing risk metrics...")

    bench_returns = df_benchmark.set_index("trade_date")["benchmark_close"].pct_change().dropna()

    avg_rf = df_rf["yield_pct"].mean() / 100

    daily_rf = avg_rf / TRADING_DAYS_PER_YEAR

    all_metrics = []

    tickers = list(daily_returns.columns)

    for ticker in tickers + ["PORTFOLIO"]:
        if ticker == "PORTFOLIO":
            ret = portfolio_daily_return.dropna()
        else:
            ret = daily_returns[ticker].dropna()

        for period_name, period_days in LOOKBACK_PERIODS.items():
            if period_days is not None and len(ret) > period_days:
                ret_slice = ret.iloc[-period_days:]
            else:
                ret_slice = ret

            if len(ret_slice) < 30: 
                continue

            n_days = len(ret_slice)

           
            cumulative = (1 + ret_slice).prod() - 1
            ann_return = (1 + cumulative) ** (TRADING_DAYS_PER_YEAR / n_days) - 1

            ann_vol = ret_slice.std() * np.sqrt(TRADING_DAYS_PER_YEAR)

            sharpe = (ann_return - avg_rf) / ann_vol if ann_vol > 0 else 0

            downside_returns = ret_slice[ret_slice < 0]
            downside_std = downside_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
            sortino = (ann_return - avg_rf) / downside_std if downside_std > 0 else 0

            var_95 = float(np.percentile(ret_slice, 5))

            cvar_95 = float(ret_slice[ret_slice <= var_95].mean()) if len(ret_slice[ret_slice <= var_95]) > 0 else var_95

            cum_ret_series = (1 + ret_slice).cumprod()
            running_max = cum_ret_series.cummax()
            drawdowns = cum_ret_series / running_max - 1
            max_dd = float(drawdowns.min())

            common_idx = ret_slice.index.intersection(bench_returns.index)
            if len(common_idx) > 30:
                stock_aligned = ret_slice.loc[common_idx]
                bench_aligned = bench_returns.loc[common_idx]

                covariance = np.cov(stock_aligned, bench_aligned)[0][1]
                bench_variance = np.var(bench_aligned, ddof=1)
                beta = covariance / bench_variance if bench_variance > 0 else 1.0

                bench_ann_return = (1 + bench_aligned).prod() ** (TRADING_DAYS_PER_YEAR / len(bench_aligned)) - 1
                expected_return = avg_rf + beta * (bench_ann_return - avg_rf)
                alpha = ann_return - expected_return

                excess_returns = stock_aligned - bench_aligned
                tracking_error = excess_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)

                info_ratio = (ann_return - bench_ann_return) / tracking_error if tracking_error > 0 else 0
            else:
                beta = None
                alpha = None
                tracking_error = None
                info_ratio = None

            skewness = float(ret_slice.skew())
            kurtosis = float(ret_slice.kurtosis())

            metrics = {
                "annualized_return": ann_return,
                "annualized_volatility": ann_vol,
                "sharpe_ratio": sharpe,
                "sortino_ratio": sortino,
                "var_95": var_95,
                "cvar_95": cvar_95,
                "max_drawdown": max_dd,
                "beta": beta,
                "alpha": alpha,
                "tracking_error": tracking_error,
                "information_ratio": info_ratio,
                "skewness": skewness,
                "kurtosis": kurtosis,
                "total_return": cumulative,
                "num_trading_days": n_days,
            }

            as_of_date = ret_slice.index[-1].strftime("%Y-%m-%d")

            for metric_name, metric_value in metrics.items():
                if metric_value is not None:
                    all_metrics.append({
                        "ticker": ticker,
                        "metric_name": metric_name,
                        "metric_value": round(float(metric_value), 8),
                        "as_of_date": as_of_date,
                        "lookback_period": period_name,
                    })

    df_metrics = pd.DataFrame(all_metrics)

    port_metrics = df_metrics[
        (df_metrics["ticker"] == "PORTFOLIO") & (df_metrics["lookback_period"] == "ALL")
    ].set_index("metric_name")["metric_value"]

    print(f"\n  ── Portfolio Risk Summary (All Time) ──")
    print(f"  Annualized Return:  {port_metrics.get('annualized_return', 0):.2%}")
    print(f"  Annualized Vol:     {port_metrics.get('annualized_volatility', 0):.2%}")
    print(f"  Sharpe Ratio:       {port_metrics.get('sharpe_ratio', 0):.4f}")
    print(f"  Sortino Ratio:      {port_metrics.get('sortino_ratio', 0):.4f}")
    print(f"  VaR (95%):          {port_metrics.get('var_95', 0):.2%}")
    print(f"  CVaR (95%):         {port_metrics.get('cvar_95', 0):.2%}")
    print(f"  Max Drawdown:       {port_metrics.get('max_drawdown', 0):.2%}")
    print(f"  Beta:               {port_metrics.get('beta', 0):.4f}")
    print(f"  Alpha:              {port_metrics.get('alpha', 0):.2%}")

    print(f"\n  Computed {len(df_metrics):,} metric records for {df_metrics['ticker'].nunique()} entities")

    return df_metrics

# 3. SECTOR ANALYSIS

def compute_sector_analysis(price_pivot, df_holdings, daily_returns):
    """
    Compute sector-level portfolio allocation and performance.
    
    Metrics per sector:
        - Total market value
        - Portfolio weight (%)
        - Sector return (weighted)
    """
    print("\n Computing sector analysis...")

    shares = df_holdings.set_index("ticker")["shares_held"]
    sector_map = df_holdings.set_index("ticker")["sector"]

    latest_date = price_pivot.index[-1]
    latest_prices = price_pivot.loc[latest_date]

    common_tickers = list(set(shares.index) & set(latest_prices.index))
    market_values = (shares[common_tickers] * latest_prices[common_tickers])
    total_value = market_values.sum()

    records = []
    for sector in sector_map[common_tickers].unique():
        sector_tickers = [t for t in common_tickers if sector_map.get(t) == sector]

        sector_mv = market_values[sector_tickers].sum()
        sector_weight = sector_mv / total_value

        sector_returns = daily_returns[sector_tickers].mean(axis=1)
        sector_cum_return = float((1 + sector_returns).prod() - 1)

        records.append({
            "sector": sector,
            "total_market_value": round(float(sector_mv), 2),
            "portfolio_weight": round(float(sector_weight), 6),
            "sector_return": round(sector_cum_return, 6),
            "as_of_date": latest_date.strftime("%Y-%m-%d"),
        })

    df_sectors = pd.DataFrame(records).sort_values("portfolio_weight", ascending=False)

    print(f"\n   Sector Allocation ")
    for _, row in df_sectors.iterrows():
        print(f"  {row['sector']:<15} Weight: {row['portfolio_weight']:>7.1%}  "
              f"Return: {row['sector_return']:>8.1%}  "
              f"Value: ${row['total_market_value']:>12,.2f}")

    hhi = (df_sectors["portfolio_weight"] ** 2).sum()
    print(f"\n  HHI (concentration): {hhi:.4f} (1/{len(df_sectors)} = {1/len(df_sectors):.4f} = perfectly diversified)")

    print(f"  Sector analysis complete for {len(df_sectors)} sectors")
    return df_sectors

# 4. CORRELATION MATRIX


def compute_correlation_matrix(daily_returns):
    """
    Compute pairwise Pearson correlation between all stocks.
    """
    print("\n Computing correlation matrix...")

    corr_matrix = daily_returns.corr()

    records = []
    tickers = corr_matrix.columns.tolist()
    for i, t1 in enumerate(tickers):
        for j, t2 in enumerate(tickers):
            if i <= j:  # Upper triangle + diagonal
                records.append({
                    "ticker_1": t1,
                    "ticker_2": t2,
                    "correlation": round(float(corr_matrix.loc[t1, t2]), 6),
                    "lookback_period": "ALL",
                })

    df_corr = pd.DataFrame(records)

    non_self = df_corr[df_corr["ticker_1"] != df_corr["ticker_2"]]
    if len(non_self) > 0:
        highest = non_self.loc[non_self["correlation"].idxmax()]
        lowest = non_self.loc[non_self["correlation"].idxmin()]
        print(f"  Highest correlation: {highest['ticker_1']}-{highest['ticker_2']} = {highest['correlation']:.4f}")
        print(f"  Lowest correlation:  {lowest['ticker_1']}-{lowest['ticker_2']} = {lowest['correlation']:.4f}")

    print(f"  Computed {len(df_corr)} correlation pairs")
    return df_corr

# 5. WRITE RESULTS TO DATABASE

def write_results_to_db(df_returns, df_portfolio, df_metrics, df_sectors, df_corr):
    """Write all computed results back to SQLite database."""
    print("\n Writing computed results to database...")

    conn = sqlite3.connect(DB_PATH)

    try:
        tables = [
            "computed_daily_returns",
            "computed_portfolio_summary",
            "computed_risk_metrics",
            "computed_sector_analysis",
            "computed_correlation_matrix",
        ]
        for table in tables:
            conn.execute(f"DELETE FROM {table}")

        df_returns.to_sql("computed_daily_returns", conn, if_exists="append", index=False)
        print(f" computed_daily_returns:      {len(df_returns):>8,} rows")

        df_portfolio.to_sql("computed_portfolio_summary", conn, if_exists="append", index=False)
        print(f" computed_portfolio_summary:  {len(df_portfolio):>8,} rows")

        df_metrics.to_sql("computed_risk_metrics", conn, if_exists="append", index=False)
        print(f" computed_risk_metrics:       {len(df_metrics):>8,} rows")

        df_sectors.to_sql("computed_sector_analysis", conn, if_exists="append", index=False)
        print(f" computed_sector_analysis:    {len(df_sectors):>8,} rows")

        df_corr.to_sql("computed_correlation_matrix", conn, if_exists="append", index=False)
        print(f" computed_correlation_matrix: {len(df_corr):>8,} rows")

        conn.commit()
        print(f"\n All computed data written to {DB_PATH}")

    except Exception as e:
        conn.rollback()
        print(f"\n  Error writing to database: {e}")
        raise
    finally:
        conn.close()

# MAIN EXECUTION

def main():
    print("=" * 60)
    print(" FINANCIAL PORTFOLIO ANALYTICS — COMPUTE ENGINE")
    print("=" * 60)

    df_prices, df_holdings, df_benchmark, df_rf = load_data_from_db()

    df_returns, daily_returns, cumulative_returns, price_pivot = compute_stock_returns(df_prices)

    df_portfolio, portfolio_daily_return, weights, total_value = compute_portfolio_returns(
        daily_returns, price_pivot, df_holdings
    )

    df_metrics = compute_risk_metrics(daily_returns, portfolio_daily_return, df_benchmark, df_rf)
    df_sectors = compute_sector_analysis(price_pivot, df_holdings, daily_returns)
    df_corr = compute_correlation_matrix(daily_returns)

    write_results_to_db(df_returns, df_portfolio, df_metrics, df_sectors, df_corr)

    print("\n" + "=" * 60)
    print(" ANALYTICS ENGINE — COMPLETE")
    print("=" * 60)
    print(f"  Daily returns:       {len(df_returns):>8,} records")
    print(f"  Portfolio summary:   {len(df_portfolio):>8,} records")
    print(f"  Risk metrics:        {len(df_metrics):>8,} records")
    print(f"  Sector analysis:     {len(df_sectors):>8,} records")
    print(f"  Correlations:        {len(df_corr):>8,} records")
    print("=" * 60)
    print("  Next step: Run 05_create_sql_views.py for Tableau views")
    print("=" * 60)

    return df_returns, df_portfolio, df_metrics, df_sectors, df_corr


if __name__ == "__main__":
    main()
