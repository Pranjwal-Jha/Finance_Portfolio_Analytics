"""
06_run_pipeline.py — Master Pipeline Script

Runs the complete data pipeline end-to-end:
    1. Fetch latest market data
    2. Load into SQLite database
    3. Compute all analytics
    4. Create/refresh SQL views for Tableau
    5. Export CSVs for Tableau Public

Can be scheduled to run daily via Windows Task Scheduler.
"""

import os
import sys
import time
import sqlite3
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

DB_PATH = os.path.join(PROJECT_ROOT, os.getenv("DB_PATH", "data/portfolio.db"))


def log(message):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"  [{timestamp}] {message}")


def run_step(step_name, func):
    """Run a pipeline step with timing and error handling."""
    print(f"\n{'─' * 50}")
    print(f"  STEP: {step_name}")
    print(f"{'─' * 50}")

    start = time.time()
    try:
        func()
        elapsed = time.time() - start
        log(f" Completed in {elapsed:.1f}s")
        return True
    except Exception as e:
        elapsed = time.time() - start
        log(f" Failed after {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        return False


def step_fetch_data():
    """Step 1: Fetch latest market data."""
    from scripts.fetch_data_module import main as fetch_main
    fetch_main()


def step_load_to_sqlite():
    """Step 2: Load data into SQLite."""
    from scripts.load_module import main as load_main
    load_main()


def step_compute_analytics():
    """Step 3: Compute all analytics."""
    from scripts.compute_module import main as compute_main
    compute_main()


def step_create_views():
    """Step 4: Create SQL views for Tableau."""
    from scripts.views_module import create_views
    create_views()


def step_export_csvs():
    """Step 5: Export views as CSVs for Tableau Public."""
    log("Exporting views as CSVs...")

    conn = sqlite3.connect(DB_PATH)
    views = [
        "vw_portfolio_performance", "vw_risk_dashboard",
        "vw_sector_allocation", "vw_benchmark_comparison",
        "vw_stock_detail", "vw_monthly_returns",
        "vw_correlation_matrix", "vw_top_movers",
    ]

    export_dir = os.path.join(PROJECT_ROOT, "tableau", "csv_exports")
    os.makedirs(export_dir, exist_ok=True)

    for view in views:
        df = pd.read_sql(f"SELECT * FROM {view}", conn)
        df.to_csv(os.path.join(export_dir, f"{view}.csv"), index=False)
        log(f"  Exported {view}: {len(df):,} rows")

    conn.close()


def main():
    pipeline_start = time.time()

    print("=" * 60)
    print(" FINANCIAL PORTFOLIO ANALYTICS — DAILY PIPELINE")
    print(f"   Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = {}

    # Step 1: Fetch data
    print(f"\n{'─' * 50}")
    print(f"  STEP 1: Fetch Market Data")
    print(f"{'─' * 50}")
    start = time.time()
    try:
        exec(open(os.path.join(PROJECT_ROOT, "scripts", "01_fetch_data.py")).read())
        results["Fetch Data"] = True
        log(f" Completed in {time.time() - start:.1f}s")
    except Exception as e:
        results["Fetch Data"] = False
        log(f" Failed: {e}")

    # Step 2: Load to SQLite
    print(f"\n{'─' * 50}")
    print(f"  STEP 2: Load to SQLite")
    print(f"{'─' * 50}")
    start = time.time()
    try:
        exec(open(os.path.join(PROJECT_ROOT, "scripts", "02_load_to_sqlite.py")).read())
        results["Load SQLite"] = True
        log(f" Completed in {time.time() - start:.1f}s")
    except Exception as e:
        results["Load SQLite"] = False
        log(f" Failed: {e}")

    # Step 3: Compute analytics
    print(f"\n{'─' * 50}")
    print(f"  STEP 3: Compute Analytics")
    print(f"{'─' * 50}")
    start = time.time()
    try:
        exec(open(os.path.join(PROJECT_ROOT, "scripts", "03_compute_analytics.py")).read())
        results["Compute Analytics"] = True
        log(f" Completed in {time.time() - start:.1f}s")
    except Exception as e:
        results["Compute Analytics"] = False
        log(f" Failed: {e}")

    # Step 4: Create SQL views
    print(f"\n{'─' * 50}")
    print(f"  STEP 4: Create SQL Views")
    print(f"{'─' * 50}")
    start = time.time()
    try:
        exec(open(os.path.join(PROJECT_ROOT, "scripts", "05_create_sql_views.py")).read())
        results["SQL Views"] = True
        log(f" Completed in {time.time() - start:.1f}s")
    except Exception as e:
        results["SQL Views"] = False
        log(f" Failed: {e}")

    # Step 5: Export CSVs
    print(f"\n{'─' * 50}")
    print(f"  STEP 5: Export CSVs")
    print(f"{'─' * 50}")
    start = time.time()
    try:
        step_export_csvs()
        results["Export CSVs"] = True
        log(f" Completed in {time.time() - start:.1f}s")
    except Exception as e:
        results["Export CSVs"] = False
        log(f" Failed: {e}")

    # Pipeline summary
    total_time = time.time() - pipeline_start
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)

    print("\n" + "=" * 60)
    print(" PIPELINE SUMMARY")
    print("=" * 60)
    for step_name, success in results.items():
        status = "success" if success else "no success"
        print(f"  {status} {step_name}")
    print(f"\n  Total: {passed} passed, {failed} failed")
    print(f"  Duration: {total_time:.1f}s ({total_time/60:.1f} minutes)")
    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
