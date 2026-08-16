"""
04_generate_dashboard.py — Generate Interactive HTML Dashboards

Reads computed data from SQLite and generates a self-contained HTML file
with 3 interactive dashboards using Plotly.js:
    1. Executive Portfolio Overview
    2. Risk Analytics Deep-Dive
    3. Individual Stock Analysis

The HTML file can be opened directly in any browser — no server needed.
"""

import os
import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, os.getenv("DB_PATH", "data/portfolio.db"))
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "dashboard.html")


def load_all_data():
    """Load all computed data from SQLite."""
    print("Loading data from database...")
    conn = sqlite3.connect(DB_PATH)

    data = {}
    data["benchmark"] = pd.read_sql("SELECT * FROM vw_benchmark_comparison ORDER BY trade_date", conn)
    data["risk"] = pd.read_sql("SELECT * FROM vw_risk_dashboard", conn)
    data["sectors"] = pd.read_sql("SELECT * FROM vw_sector_allocation", conn)
    data["monthly"] = pd.read_sql("SELECT * FROM vw_monthly_returns ORDER BY year, month", conn)
    data["movers"] = pd.read_sql("SELECT * FROM vw_top_movers ORDER BY total_return DESC", conn)
    data["correlation"] = pd.read_sql("SELECT * FROM vw_correlation_matrix", conn)
    data["stock_detail"] = pd.read_sql("SELECT * FROM vw_stock_detail ORDER BY ticker, trade_date", conn)
    data["portfolio_summary"] = pd.read_sql("SELECT * FROM computed_portfolio_summary ORDER BY trade_date", conn)
    data["holdings"] = pd.read_sql("SELECT * FROM portfolio_holdings", conn)

    conn.close()
    print("Data loaded successfully.")
    return data


def prepare_json_data(data):
    """Convert DataFrames to JSON for embedding in HTML."""
    json_data = {}

    bench = data["benchmark"]
    json_data["benchmark"] = {
        "dates": bench["trade_date"].tolist(),
        "portfolio_return": (bench["portfolio_cumulative_return"].fillna(0) * 100).round(2).tolist(),
        "benchmark_return": (bench["benchmark_cumulative_return"].fillna(0) * 100).round(2).tolist(),
        "portfolio_value": bench["total_portfolio_value"].round(2).tolist(),
        "drawdown": (bench["portfolio_drawdown"].fillna(0) * 100).round(2).tolist(),
    }

    risk_port = data["risk"][(data["risk"]["ticker"] == "PORTFOLIO") & (data["risk"]["lookback_period"] == "ALL")]
    if len(risk_port) > 0:
        r = risk_port.iloc[0]
        json_data["portfolio_kpis"] = {
            "total_value": round(float(bench["total_portfolio_value"].iloc[-1]), 2),
            "total_return": round(float(r.get("total_return", 0)) * 100, 2),
            "ann_return": round(float(r.get("annualized_return", 0)) * 100, 2),
            "ann_vol": round(float(r.get("annualized_volatility", 0)) * 100, 2),
            "sharpe": round(float(r.get("sharpe_ratio", 0)), 4),
            "sortino": round(float(r.get("sortino_ratio", 0)), 4),
            "var_95": round(float(r.get("var_95", 0)) * 100, 2),
            "cvar_95": round(float(r.get("cvar_95", 0)) * 100, 2),
            "max_dd": round(float(r.get("max_drawdown", 0)) * 100, 2),
            "beta": round(float(r.get("beta", 0)), 4),
            "alpha": round(float(r.get("alpha", 0)) * 100, 2),
        }

    sectors = data["sectors"]
    json_data["sectors"] = {
        "names": sectors["sector"].tolist(),
        "weights": (sectors["portfolio_weight"] * 100).round(2).tolist(),
        "returns": (sectors["sector_return"] * 100).round(2).tolist(),
        "values": sectors["total_market_value"].round(2).tolist(),
        "num_stocks": sectors["num_stocks"].tolist(),
    }

    monthly = data["monthly"]
    json_data["monthly"] = {
        "years": monthly["year"].tolist(),
        "months": monthly["month_name"].tolist(),
        "returns": (monthly["monthly_return"] * 100).round(2).tolist(),
    }

    movers = data["movers"]
    json_data["movers"] = {
        "tickers": movers["ticker"].tolist(),
        "names": movers["company_name"].tolist(),
        "returns": (movers["total_return"] * 100).round(2).tolist(),
        "sectors": movers["sector"].tolist(),
    }

    risk_all = data["risk"][data["risk"]["lookback_period"] == "ALL"].copy()
    risk_stocks = risk_all[risk_all["ticker"] != "PORTFOLIO"]
    json_data["stock_risk"] = {
        "tickers": risk_stocks["ticker"].tolist(),
        "names": risk_stocks["display_name"].tolist(),
        "ann_return": (risk_stocks["annualized_return"].fillna(0) * 100).round(2).tolist(),
        "ann_vol": (risk_stocks["annualized_volatility"].fillna(0) * 100).round(2).tolist(),
        "sharpe": risk_stocks["sharpe_ratio"].fillna(0).round(4).tolist(),
        "beta": risk_stocks["beta"].fillna(0).round(4).tolist(),
        "max_dd": (risk_stocks["max_drawdown"].fillna(0) * 100).round(2).tolist(),
        "alpha": (risk_stocks["alpha"].fillna(0) * 100).round(2).tolist(),
    }

    corr = data["correlation"]
    tickers = sorted(corr["ticker_1"].unique())
    corr_matrix = []
    for t2 in tickers:
        row = []
        for t1 in tickers:
            val = corr[(corr["ticker_1"] == t1) & (corr["ticker_2"] == t2)]["correlation"]
            if len(val) == 0:
                val = corr[(corr["ticker_1"] == t2) & (corr["ticker_2"] == t1)]["correlation"]
            row.append(round(float(val.iloc[0]), 3) if len(val) > 0 else 0)
        corr_matrix.append(row)
    json_data["correlation"] = {
        "tickers": tickers,
        "matrix": corr_matrix,
    }

    ps = data["portfolio_summary"]
    daily_rets = ps["daily_return"].dropna().tolist()
    json_data["return_dist"] = [round(r * 100, 4) for r in daily_rets]

    stock_data = {}
    for ticker in data["holdings"]["ticker"].unique():
        sd = data["stock_detail"][data["stock_detail"]["ticker"] == ticker]
        if len(sd) == 0:
            continue
        stock_data[ticker] = {
            "dates": sd["trade_date"].tolist(),
            "close": sd["adj_close"].round(2).tolist(),
            "volume": sd["volume"].tolist(),
            "ma7": sd["ma_7d"].round(2).tolist(),
            "ma30": sd["ma_30d"].round(2).tolist(),
            "ma90": sd["ma_90d"].round(2).tolist(),
            "cum_return": (sd["cumulative_return"].fillna(0) * 100).round(2).tolist(),
            "company": sd["company_name"].iloc[0] if "company_name" in sd.columns else ticker,
            "sector": sd["sector"].iloc[0] if "sector" in sd.columns else "",
        }
    json_data["stocks"] = stock_data

    return json_data


