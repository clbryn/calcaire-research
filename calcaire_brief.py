#!/usr/bin/env python3
"""
Calcaire Research — Equity Brief Generator
Usage: python calcaire_brief.py <TICKER>
"""

import sys

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance is not installed.")
    print("Run:  pip install yfinance")
    sys.exit(1)


import argparse
from datetime import date


# ── Formatting helpers ─────────────────────────────────────────────────────────

def fmt_currency(val, decimals=2):
    if val is None:
        return "N/A"
    try:
        val = float(val)
        if abs(val) >= 1e12:
            return f"${val / 1e12:.{decimals}f}T"
        if abs(val) >= 1e9:
            return f"${val / 1e9:.{decimals}f}B"
        if abs(val) >= 1e6:
            return f"${val / 1e6:.{decimals}f}M"
        return f"${val:,.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def fmt_ratio(val, decimals=2):
    if val is None:
        return "N/A"
    try:
        return f"{float(val):.{decimals}f}x"
    except (TypeError, ValueError):
        return "N/A"


def fmt_pct(val, decimals=1):
    if val is None:
        return "N/A"
    try:
        return f"{float(val) * 100:.{decimals}f}%"
    except (TypeError, ValueError):
        return "N/A"


def fmt_price(val, decimals=2):
    if val is None:
        return "N/A"
    try:
        return f"${float(val):,.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def safe_get(info, *keys, default=None):
    """Return the first key found in info dict, or default."""
    for key in keys:
        val = info.get(key)
        if val is not None:
            return val
    return default


# ── Data fetch ─────────────────────────────────────────────────────────────────

def fetch_data(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    info = t.info or {}

    # Basic identity
    data = {
        "ticker":       ticker.upper(),
        "company":      safe_get(info, "longName", "shortName", default="N/A"),
        "sector":       safe_get(info, "sector",   default="N/A"),
        "industry":     safe_get(info, "industry", default="N/A"),
        "market_cap":   safe_get(info, "marketCap"),
        "currency":     safe_get(info, "currency", default="USD"),
    }

    # Price
    data["price"]       = safe_get(info, "currentPrice", "regularMarketPrice",
                                   "previousClose")
    data["week52_high"] = safe_get(info, "fiftyTwoWeekHigh")
    data["week52_low"]  = safe_get(info, "fiftyTwoWeekLow")

    # Valuation
    data["pe_trailing"] = safe_get(info, "trailingPE")
    data["pe_forward"]  = safe_get(info, "forwardPE")
    data["ev_ebitda"]   = safe_get(info, "enterpriseToEbitda")

    # Financials
    data["revenue"]        = safe_get(info, "totalRevenue")
    data["net_income"]     = safe_get(info, "netIncomeToCommon")
    data["profit_margin"]  = safe_get(info, "profitMargins")
    data["free_cash_flow"] = safe_get(info, "freeCashflow")

    # Balance sheet
    data["debt_to_equity"] = safe_get(info, "debtToEquity")

    # Analyst consensus
    data["target_price"]        = safe_get(info, "targetMeanPrice")
    data["target_high"]         = safe_get(info, "targetHighPrice")
    data["target_low"]          = safe_get(info, "targetLowPrice")
    data["recommendation"]      = safe_get(info, "recommendationKey", default="N/A")
    data["num_analyst_opinions"]= safe_get(info, "numberOfAnalystOpinions")

    return data


# ── Brief builder ──────────────────────────────────────────────────────────────

DIVIDER = "═" * 64
THIN    = "─" * 64


def build_brief(data: dict, today: str) -> str:
    ticker = data["ticker"]
    rec    = str(data["recommendation"]).replace("-", " ").upper()

    # Debt-to-equity: yfinance returns it as a plain ratio (not %)
    de_raw = data.get("debt_to_equity")
    if de_raw is not None:
        try:
            de_str = f"{float(de_raw):.2f}x"
        except (TypeError, ValueError):
            de_str = "N/A"
    else:
        de_str = "N/A"

    num_opinions = data.get("num_analyst_opinions")
    opinions_str = f"({int(num_opinions)} analysts)" if num_opinions else ""

    lines = [
        "",
        DIVIDER,
        "  CALCAIRE RESEARCH",
        f"  Equity Brief — {ticker}",
        f"  Generated: {today}",
        DIVIDER,
        "",
        f"  Company   : {data['company']}",
        f"  Sector    : {data['sector']}",
        f"  Industry  : {data['industry']}",
        f"  Market Cap: {fmt_currency(data['market_cap'])}",
        "",
        THIN,
        "  PRICE & TRADING",
        THIN,
        f"  Current Price : {fmt_price(data['price'])}",
        f"  52-Week High  : {fmt_price(data['week52_high'])}",
        f"  52-Week Low   : {fmt_price(data['week52_low'])}",
        "",
        THIN,
        "  VALUATION",
        THIN,
        f"  Trailing P/E  : {fmt_ratio(data['pe_trailing'])}",
        f"  Forward P/E   : {fmt_ratio(data['pe_forward'])}",
        f"  EV / EBITDA   : {fmt_ratio(data['ev_ebitda'])}",
        "",
        THIN,
        "  FINANCIALS (TTM)",
        THIN,
        f"  Revenue        : {fmt_currency(data['revenue'])}",
        f"  Net Income     : {fmt_currency(data['net_income'])}",
        f"  Profit Margin  : {fmt_pct(data['profit_margin'])}",
        f"  Free Cash Flow : {fmt_currency(data['free_cash_flow'])}",
        "",
        THIN,
        "  BALANCE SHEET",
        THIN,
        f"  Debt / Equity  : {de_str}",
        "",
        THIN,
        "  ANALYST CONSENSUS",
        THIN,
        f"  Recommendation : {rec} {opinions_str.strip()}",
        f"  Price Target   : {fmt_price(data['target_price'])}",
        f"  Target Range   : {fmt_price(data['target_low'])} — {fmt_price(data['target_high'])}",
        "",
        DIVIDER,
        "  Calcaire Research | For informational purposes only.",
        "  Not investment advice.",
        DIVIDER,
        "",
    ]

    return "\n".join(lines)


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Calcaire Research — Equity Brief Generator"
    )
    parser.add_argument("ticker", help="Stock ticker symbol (e.g. NVDA)")
    args = parser.parse_args()

    ticker = args.ticker.strip().upper()
    today  = date.today().isoformat()

    print(f"\nFetching data for {ticker}...")

    try:
        data = fetch_data(ticker)
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        sys.exit(1)

    if data["company"] == "N/A" and data["price"] is None:
        print(f"No data found for ticker '{ticker}'. "
              "Please check the symbol and try again.")
        sys.exit(1)

    brief = build_brief(data, today)

    # Print to terminal
    print(brief)

    # Export to .txt
    filename = f"{ticker}_{today}.txt"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(brief)
        print(f"Brief saved to {filename}\n")
    except OSError as e:
        print(f"Warning: could not write file '{filename}': {e}")


if __name__ == "__main__":
    main()
