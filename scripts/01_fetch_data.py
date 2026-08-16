"""
01_fetch_data.py  Fetch market data from Yahoo Finance

Fetches:
    1. Daily OHLCV prices for all portfolio stocks (3+ years)
    2. S&P 500 benchmark prices (^GSPC)
    3. US 10-Year Treasury yield as risk-free rate (^TNX)
    4. Company metadata (name, sector, industry, market_cap)

All raw data is saved as CSV backups in data/backups/
"""

import os
import sys
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv
from tqdm import tqdm

# Configuration

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTFOLIO_CSV = os.path.join(PROJECT_ROOT, "portfolio_config.csv")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "data", "backups")

START_DATE = os.getenv("DATA_START_DATE", "2022-01-01")
END_DATE = os.getenv("DATA_END_DATE", "") or datetime.today().strftime("%Y-%m-%d")

BENCHMARK_TICKER = os.getenv("BENCHMARK_TICKER", "^GSPC")
RISK_FREE_TICKER = os.getenv("RISK_FREE_TICKER", "^TNX")


def ensure_directories():
    """Create backup directory if it doesn't exist."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    print(f"  Backup directory: {BACKUP_DIR}")


def load_portfolio_config():
    """Load portfolio holdings from CSV."""
    print("\n Loading portfolio configuration...")
    df = pd.read_csv(PORTFOLIO_CSV)
    tickers = df["ticker"].tolist()
    print(f"  Found {len(tickers)} stocks: {', '.join(tickers)}")
    return df, tickers


def fetch_stock_prices(tickers):
    """
    Fetch daily OHLCV data for all portfolio stocks.
    Uses yfinance batch download for efficiency.
    """
    print(f"\n Fetching stock prices ({START_DATE} to {END_DATE})...")
    print(f"  Downloading data for {len(tickers)} tickers...")

    raw_data = yf.download(
        tickers=tickers,
        start=START_DATE,
        end=END_DATE,
        auto_adjust=False,
        progress=True,
        threads=True,
    )

    records = []
    for ticker in tqdm(tickers, desc="  Processing tickers"):
        try:
            if len(tickers) == 1:
                ticker_data = raw_data.copy()
            else:
                ticker_data = raw_data.xs(ticker, level="Ticker", axis=1)

            for date, row in ticker_data.iterrows():
                records.append({
                    "ticker": ticker,
                    "trade_date": date.strftime("%Y-%m-%d"),
                    "open_price": round(float(row["Open"]), 4) if pd.notna(row["Open"]) else None,
                    "high_price": round(float(row["High"]), 4) if pd.notna(row["High"]) else None,
                    "low_price": round(float(row["Low"]), 4) if pd.notna(row["Low"]) else None,
                    "close_price": round(float(row["Close"]), 4) if pd.notna(row["Close"]) else None,
                    "adj_close": round(float(row["Adj Close"]), 4) if pd.notna(row["Adj Close"]) else None,
                    "volume": int(row["Volume"]) if pd.notna(row["Volume"]) else None,
                })
        except Exception as e:
            print(f"  Error processing {ticker}: {e}")

    df_prices = pd.DataFrame(records)

    df_prices = df_prices.dropna(subset=["adj_close"])

    print(f"  Fetched {len(df_prices):,} price records for {df_prices['ticker'].nunique()} stocks")
    print(f"  Date range: {df_prices['trade_date'].min()} to {df_prices['trade_date'].max()}")

    return df_prices


def fetch_benchmark(ticker="^GSPC"):
    """Fetch S&P 500 benchmark daily prices."""
    print(f"\n Fetching benchmark data ({ticker})...")

    bench_data = yf.download(
        tickers=ticker,
        start=START_DATE,
        end=END_DATE,
        auto_adjust=False,
        progress=False,
    )

    if isinstance(bench_data.columns, pd.MultiIndex):
        bench_data = bench_data.droplevel("Ticker", axis=1)

    df_bench = pd.DataFrame({
        "trade_date": bench_data.index.strftime("%Y-%m-%d"),
        "close_price": bench_data["Close"].round(4).values,
    }).dropna()

    print(f" Fetched {len(df_bench):,} benchmark records")
    print(f"  Date range: {df_bench['trade_date'].min()} to {df_bench['trade_date'].max()}")

    return df_bench


def fetch_risk_free_rate(ticker="^TNX"):
    """Fetch US 10-Year Treasury yield as risk-free rate proxy."""
    print(f"\nFetching risk-free rate ({ticker})...")

    rf_data = yf.download(
        tickers=ticker,
        start=START_DATE,
        end=END_DATE,
        auto_adjust=False,
        progress=False,
    )

    if isinstance(rf_data.columns, pd.MultiIndex):
        rf_data = rf_data.droplevel("Ticker", axis=1)

    df_rf = pd.DataFrame({
        "rate_date": rf_data.index.strftime("%Y-%m-%d"),
        "yield_pct": rf_data["Close"].round(4).values,
    }).dropna()

    print(f"  Fetched {len(df_rf):,} risk-free rate records")
    print(f"  Latest yield: {df_rf['yield_pct'].iloc[-1]:.2f}%")

    return df_rf


def fetch_company_metadata(tickers):
    """Fetch company info (name, sector, industry, market cap) for each ticker."""
    print(f"\n Fetching company metadata for {len(tickers)} stocks...")

    records = []
    for ticker in tqdm(tickers, desc="  Fetching info"):
        try:
            info = yf.Ticker(ticker).info
            records.append({
                "ticker": ticker,
                "company_name": info.get("longName") or info.get("shortName", ticker),
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown"),
                "market_cap": info.get("marketCap", None),
                "last_updated": datetime.today().strftime("%Y-%m-%d"),
            })
        except Exception as e:
            print(f" Could not fetch info for {ticker}: {e}")
            records.append({
                "ticker": ticker,
                "company_name": ticker,
                "sector": "Unknown",
                "industry": "Unknown",
                "market_cap": None,
                "last_updated": datetime.today().strftime("%Y-%m-%d"),
            })

    df_meta = pd.DataFrame(records)
    print(f" Fetched metadata for {len(df_meta)} companies")

    return df_meta


def save_csv_backups(df_prices, df_benchmark, df_risk_free, df_metadata, df_holdings):
    """Save all DataFrames as CSV backups."""
    print("\n Saving CSV backups...")

    timestamp = datetime.now().strftime("%Y%m%d")

    files = {
        f"stock_prices_{timestamp}.csv": df_prices,
        f"benchmark_prices_{timestamp}.csv": df_benchmark,
        f"risk_free_rate_{timestamp}.csv": df_risk_free,
        f"company_metadata_{timestamp}.csv": df_metadata,
        f"portfolio_holdings_{timestamp}.csv": df_holdings,
    }

    for filename, df in files.items():
        filepath = os.path.join(BACKUP_DIR, filename)
        df.to_csv(filepath, index=False)
        print(f" Saved {filename} ({len(df):,} rows)")


def print_summary(df_prices, df_benchmark, df_risk_free, df_metadata):
    """Print a summary of all fetched data."""
    print("\n" + "=" * 60)
    print(" DATA COLLECTION SUMMARY")
    print("=" * 60)
    print(f"  Stock Prices:     {len(df_prices):>8,} rows  |  {df_prices['ticker'].nunique()} stocks")
    print(f"  Benchmark (S&P):  {len(df_benchmark):>8,} rows")
    print(f"  Risk-Free Rate:   {len(df_risk_free):>8,} rows")
    print(f"  Company Metadata: {len(df_metadata):>8,} rows")
    print(f"  Date Range:       {df_prices['trade_date'].min()} → {df_prices['trade_date'].max()}")
    print("=" * 60)
    print("  All CSV backups saved to: data/backups/")
    print("  Next step: Run 02_load_to_sqlite.py to load into database")
    print("=" * 60)


# Main Execution

def main():
    print("=" * 60)
    print("FINANCIAL PORTFOLIO ANALYTICS — DATA COLLECTION")
    print("=" * 60)

    # Setup
    ensure_directories()

    # Step 1: Load portfolio config
    df_holdings, tickers = load_portfolio_config()

    # Step 2: Fetch stock prices
    df_prices = fetch_stock_prices(tickers)

    # Step 3: Fetch benchmark
    df_benchmark = fetch_benchmark(BENCHMARK_TICKER)

    # Step 4: Fetch risk-free rate
    df_risk_free = fetch_risk_free_rate(RISK_FREE_TICKER)

    # Step 5: Fetch company metadata
    df_metadata = fetch_company_metadata(tickers)

    # Step 6: Save CSV backups
    save_csv_backups(df_prices, df_benchmark, df_risk_free, df_metadata, df_holdings)

    # Summary
    print_summary(df_prices, df_benchmark, df_risk_free, df_metadata)

    print("\n Data collection complete!")
    return df_prices, df_benchmark, df_risk_free, df_metadata, df_holdings


if __name__ == "__main__":
    main()
