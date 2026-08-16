"""
02_load_to_sqlite.py  Load fetched data into SQLite database

Reads CSV backups from data/backups/ and loads them into the SQLite database.
Creates tables using the schema from sql/00_create_tables.sql.
Performs data validation after loading.
"""

import os
import sys
import glob
import sqlite3
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv


# Configuration

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, os.getenv("DB_PATH", "data/portfolio.db"))
BACKUP_DIR = os.path.join(PROJECT_ROOT, "data", "backups")
SCHEMA_FILE = os.path.join(PROJECT_ROOT, "sql", "00_create_tables.sql")


def get_latest_backup(prefix):
    """Find the most recent CSV backup file matching the prefix."""
    pattern = os.path.join(BACKUP_DIR, f"{prefix}_*.csv")
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f"No backup files found matching: {pattern}")
    return sorted(files)[-1]


def create_database():
    """Create SQLite database and tables from schema file."""
    print("\n  Creating SQLite database...")
    print(f"  Database path: {DB_PATH}")
    
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with open(SCHEMA_FILE, "r") as f:
        schema_sql = f.read()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript(schema_sql)
    conn.commit()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"   Created {len(tables)} tables: {', '.join(tables)}")

    conn.close()
    return tables


def load_portfolio_holdings(conn):
    """Load portfolio holdings into the database."""
    print("\n Loading portfolio holdings...")

    filepath = get_latest_backup("portfolio_holdings")
    df = pd.read_csv(filepath)

    conn.execute("DELETE FROM portfolio_holdings")

    df.to_sql(
        "portfolio_holdings",
        conn,
        if_exists="append",
        index=False,
    )

    count = conn.execute("SELECT COUNT(*) FROM portfolio_holdings").fetchone()[0]
    print(f"   Loaded {count} holdings from {os.path.basename(filepath)}")
    return count


def load_stock_prices(conn):
    """Load daily stock prices into the database."""
    print("\n Loading stock prices...")

    filepath = get_latest_backup("stock_prices")
    df = pd.read_csv(filepath)

    conn.execute("DELETE FROM daily_prices")

    chunk_size = 5000
    total_rows = 0

    for i in range(0, len(df), chunk_size):
        chunk = df.iloc[i:i + chunk_size]
        chunk.to_sql(
            "daily_prices",
            conn,
            if_exists="append",
            index=False,
        )
        total_rows += len(chunk)
        print(f"  ... loaded {total_rows:,} / {len(df):,} rows", end="\r")

    count = conn.execute("SELECT COUNT(*) FROM daily_prices").fetchone()[0]
    print(f"   Loaded {count:,} price records from {os.path.basename(filepath)}    ")
    return count


def load_benchmark_prices(conn):
    """Load benchmark (S&P 500) prices into the database."""
    print("\n Loading benchmark prices...")

    filepath = get_latest_backup("benchmark_prices")
    df = pd.read_csv(filepath)

    conn.execute("DELETE FROM benchmark_prices")

    df.to_sql(
        "benchmark_prices",
        conn,
        if_exists="append",
        index=False,
    )

    count = conn.execute("SELECT COUNT(*) FROM benchmark_prices").fetchone()[0]
    print(f"   Loaded {count:,} benchmark records from {os.path.basename(filepath)}")
    return count


def load_risk_free_rate(conn):
    """Load risk-free rate data into the database."""
    print("\nLoading risk-free rate data...")

    filepath = get_latest_backup("risk_free_rate")
    df = pd.read_csv(filepath)

    conn.execute("DELETE FROM risk_free_rate")

    df.to_sql(
        "risk_free_rate",
        conn,
        if_exists="append",
        index=False,
    )

    count = conn.execute("SELECT COUNT(*) FROM risk_free_rate").fetchone()[0]
    print(f"   Loaded {count:,} risk-free rate records from {os.path.basename(filepath)}")
    return count


def load_company_metadata(conn):
    """Load company metadata into the database."""
    print("\n Loading company metadata...")

    filepath = get_latest_backup("company_metadata")
    df = pd.read_csv(filepath)

    conn.execute("DELETE FROM company_metadata")

    df.to_sql(
        "company_metadata",
        conn,
        if_exists="append",
        index=False,
    )

    count = conn.execute("SELECT COUNT(*) FROM company_metadata").fetchone()[0]
    print(f"   Loaded {count} company records from {os.path.basename(filepath)}")
    return count


def validate_data(conn):
    """Run validation checks on the loaded data."""
    print("\n Running data validation checks...")

    checks_passed = 0
    checks_failed = 0

    tables = {
        "portfolio_holdings": 1,
        "daily_prices": 100,
        "benchmark_prices": 100,
        "risk_free_rate": 100,
        "company_metadata": 1,
    }

    for table, min_rows in tables.items():
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if count >= min_rows:
            print(f"   {table}: {count:,} rows (min: {min_rows})")
            checks_passed += 1
        else:
            print(f"   {table}: {count:,} rows (expected at least {min_rows})")
            checks_failed += 1

    null_count = conn.execute(
        "SELECT COUNT(*) FROM daily_prices WHERE adj_close IS NULL"
    ).fetchone()[0]
    if null_count == 0:
        print(f"   No NULL adj_close values in daily_prices")
        checks_passed += 1
    else:
        print(f"   {null_count} NULL adj_close values found")
        checks_failed += 1

    date_range = conn.execute(
        "SELECT MIN(trade_date), MAX(trade_date) FROM daily_prices"
    ).fetchone()
    print(f"   Price data range: {date_range[0]} → {date_range[1]}")

    missing = conn.execute("""
        SELECT ph.ticker
        FROM portfolio_holdings ph
        LEFT JOIN (SELECT DISTINCT ticker FROM daily_prices) dp ON ph.ticker = dp.ticker
        WHERE dp.ticker IS NULL
    """).fetchall()

    if not missing:
        print(f"   All portfolio tickers have price data")
        checks_passed += 1
    else:
        missing_tickers = [row[0] for row in missing]
        print(f"   Missing price data for: {', '.join(missing_tickers)}")
        checks_failed += 1

    print("\n   Sample data (latest 3 days for AAPL):")
    sample = conn.execute("""
        SELECT ticker, trade_date, close_price, adj_close, volume
        FROM daily_prices
        WHERE ticker = 'AAPL'
        ORDER BY trade_date DESC
        LIMIT 3
    """).fetchall()
    for row in sample:
        print(f"     {row[0]} | {row[1]} | Close: ${row[2]:,.2f} | AdjClose: ${row[3]:,.2f} | Vol: {row[4]:,}")

    print(f"\n  Validation: {checks_passed} passed, {checks_failed} failed")
    return checks_failed == 0


def print_database_summary(conn):
    """Print a summary of the database contents."""
    print("\n" + "=" * 60)
    print(" DATABASE SUMMARY")
    print("=" * 60)

    tables = ["portfolio_holdings", "daily_prices", "benchmark_prices",
              "risk_free_rate", "company_metadata"]
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<25} {count:>8,} rows")

    db_size = os.path.getsize(DB_PATH)
    if db_size > 1024 * 1024:
        size_str = f"{db_size / (1024*1024):.1f} MB"
    else:
        size_str = f"{db_size / 1024:.0f} KB"
    print(f"\n  Database file size: {size_str}")
    print(f"  Database location:  {DB_PATH}")
    print("=" * 60)

# Main Execution

def main():
    print("=" * 60)
    print(" FINANCIAL PORTFOLIO ANALYTICS — LOAD TO SQLITE")
    print("=" * 60)

    create_database()

    conn = sqlite3.connect(DB_PATH)

    try:
        load_portfolio_holdings(conn)
        load_stock_prices(conn)
        load_benchmark_prices(conn)
        load_risk_free_rate(conn)
        load_company_metadata(conn)

        conn.commit()

        validate_data(conn)

       
        print_database_summary(conn)

    except Exception as e:
        print(f"\n Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

    print("\n Database loaded successfully!")


if __name__ == "__main__":
    main()
