"""
EquiSage Market Data MCP Server
================================
Exposes yfinance data as MCP tools so ADK agents can call them
via the Model Context Protocol rather than importing Python directly.

Run standalone:
    python mcp_servers/market_data_server.py

The server uses FastMCP (bundled with the `mcp` package).
"""

import json
import os
import warnings
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf
from mcp.server.fastmcp import FastMCP

warnings.filterwarnings("ignore")

mcp = FastMCP("EquiSage Market Data Server")

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _safe_float(val) -> float | None:
    """Convert a value to float, returning None on failure."""
    try:
        v = float(val)
        return None if (np.isnan(v) or np.isinf(v)) else round(v, 4)
    except (TypeError, ValueError):
        return None


def _safe_ticker(symbol: str) -> tuple[yf.Ticker, dict]:
    """Return (ticker, info) with graceful fallback if yfinance is flaky."""
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}
        return t, info
    except Exception as exc:
        return yf.Ticker(symbol), {"error": str(exc)}


# ---------------------------------------------------------------------------
@mcp.tool()
def get_price_history(symbol: str, period: str = "1y") -> str:
    """
    Fetch OHLCV price history for an NSE symbol and compute technical indicators.

    Args:
        symbol: NSE ticker symbol e.g. 'RELIANCE.NS'
        period: yfinance period string e.g. '1y', '6mo', '3mo'

    Returns:
        JSON string with OHLCV summary, moving averages, RSI, MACD, volume trend.
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        if hist.empty:
            return json.dumps({"error": f"No price data returned for {symbol}. "
                               "The ticker may be invalid or yfinance rate-limited."})

        # Drop any trailing rows with NaN close prices (e.g. current day before market opens or holidays)
        hist = hist.dropna(subset=["Close"])

        if hist.empty:
            return json.dumps({"error": f"No valid price data returned for {symbol} after filtering NaN close prices."})

        close = hist["Close"]
        volume = hist["Volume"]

        # Moving averages
        ma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else None
        ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
        ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None

        # RSI (14-period Wilder)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi_series = 100 - (100 / (1 + rs))
        rsi = _safe_float(rsi_series.iloc[-1]) if not rsi_series.empty else None

        # MACD (12, 26, 9)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_histogram = macd_line - signal_line
        macd_val = _safe_float(macd_line.iloc[-1])
        signal_val = _safe_float(signal_line.iloc[-1])
        histogram_val = _safe_float(macd_histogram.iloc[-1])

        # Volume trend (avg last 5 days vs prior 20 days)
        recent_vol = volume.iloc[-5:].mean() if len(volume) >= 5 else volume.mean()
        prior_vol = volume.iloc[-25:-5].mean() if len(volume) >= 25 else volume.mean()
        
        # Ensure we have valid floats for volume comparison
        recent_vol_val = _safe_float(recent_vol)
        prior_vol_val = _safe_float(prior_vol)
        if recent_vol_val is not None and prior_vol_val is not None and prior_vol_val > 0:
            vol_trend = "increasing" if recent_vol_val > prior_vol_val * 1.1 else \
                        "decreasing" if recent_vol_val < prior_vol_val * 0.9 else "stable"
        else:
            vol_trend = "stable"

        current_price = _safe_float(close.iloc[-1])
        high_52w = _safe_float(close.tail(252).max())
        low_52w = _safe_float(close.tail(252).min())
        change_1y_pct = _safe_float(
            ((close.iloc[-1] - close.iloc[0]) / close.iloc[0]) * 100
        ) if len(close) > 1 and close.iloc[0] != 0 else None

        ma20_val = _safe_float(ma20)
        ma50_val = _safe_float(ma50)
        ma200_val = _safe_float(ma200)

        result = {
            "symbol": symbol,
            "period": period,
            "data_points": len(hist),
            "current_price": current_price,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "change_pct_period": change_1y_pct,
            "moving_averages": {
                "ma20": ma20_val,
                "ma50": ma50_val,
                "ma200": ma200_val,
                "price_vs_ma20": "above" if (ma20_val is not None and current_price is not None and current_price > ma20_val) else "below",
                "price_vs_ma50": "above" if (ma50_val is not None and current_price is not None and current_price > ma50_val) else "below",
                "price_vs_ma200": "above" if (ma200_val is not None and current_price is not None and current_price > ma200_val) else "below",
                "golden_cross": bool(ma50_val is not None and ma200_val is not None and ma50_val > ma200_val),
                "death_cross": bool(ma50_val is not None and ma200_val is not None and ma50_val < ma200_val),
            },
            "rsi": {
                "value": rsi,
                "signal": "overbought" if (rsi is not None and rsi > 70) else
                          "oversold" if (rsi is not None and rsi < 30) else "neutral",
            },
            "macd": {
                "macd_line": macd_val,
                "signal_line": signal_val,
                "histogram": histogram_val,
                "crossover": "bullish" if (histogram_val is not None and histogram_val > 0) else "bearish",
            },
            "volume": {
                "recent_avg": recent_vol_val,
                "prior_avg": prior_vol_val,
                "trend": vol_trend,
            },
            "ohlcv_tail": hist.tail(5)[["Open", "High", "Low", "Close", "Volume"]]
                               .round(2).to_dict(orient="records") if not hist.empty else [],
        }
        return json.dumps(result, default=str)

    except Exception as exc:
        return json.dumps({"error": f"Price history fetch failed for {symbol}: {exc}"})


# ---------------------------------------------------------------------------
# Tool 2 – Fundamentals / Key Ratios
# ---------------------------------------------------------------------------

@mcp.tool()
def get_financials(symbol: str) -> str:
    """
    Fetch key fundamental ratios for an NSE stock via yfinance.

    Args:
        symbol: NSE ticker e.g. 'TCS.NS'

    Returns:
        JSON string with P/E, EPS, margins, debt, growth, and valuation metrics.
    """
    try:
        ticker, info = _safe_ticker(symbol)
        if "error" in info and not info.get("trailingPE"):
            return json.dumps({"error": f"Could not fetch fundamentals for {symbol}: {info['error']}"})

        # Income statement for revenue/profit growth
        try:
            fin = ticker.financials  # columns = quarters newest first
        except Exception:
            fin = pd.DataFrame()

        revenue_growth = None
        net_income_growth = None
        if not fin.empty and fin.shape[1] >= 2:
            try:
                rev = fin.loc["Total Revenue"] if "Total Revenue" in fin.index else None
                ni = fin.loc["Net Income"] if "Net Income" in fin.index else None
                if rev is not None and len(rev) >= 2:
                    revenue_growth = _safe_float(((rev.iloc[0] - rev.iloc[1]) / abs(rev.iloc[1])) * 100)
                if ni is not None and len(ni) >= 2:
                    net_income_growth = _safe_float(((ni.iloc[0] - ni.iloc[1]) / abs(ni.iloc[1])) * 100)
            except Exception:
                pass

        # Quarterly earnings for EPS trend
        try:
            earnings_hist = ticker.quarterly_earnings
            eps_trend = earnings_hist["Actual"].tolist()[-4:] if (
                earnings_hist is not None and not earnings_hist.empty
                and "Actual" in earnings_hist.columns
            ) else []
        except Exception:
            eps_trend = []

        result = {
            "symbol": symbol,
            "company_name": info.get("longName", symbol),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "valuation": {
                "trailing_pe": _safe_float(info.get("trailingPE")),
                "forward_pe": _safe_float(info.get("forwardPE")),
                "peg_ratio": _safe_float(info.get("pegRatio")),
                "price_to_book": _safe_float(info.get("priceToBook")),
                "price_to_sales": _safe_float(info.get("priceToSalesTrailing12Months")),
                "ev_to_ebitda": _safe_float(info.get("enterpriseToEbitda")),
                "market_cap_cr": _safe_float(
                    (info.get("marketCap") or 0) / 1e7  # Convert to Crores
                ),
            },
            "profitability": {
                "gross_margin_pct": _safe_float((info.get("grossMargins") or 0) * 100),
                "operating_margin_pct": _safe_float((info.get("operatingMargins") or 0) * 100),
                "net_margin_pct": _safe_float((info.get("profitMargins") or 0) * 100),
                "roe_pct": _safe_float((info.get("returnOnEquity") or 0) * 100),
                "roa_pct": _safe_float((info.get("returnOnAssets") or 0) * 100),
            },
            "growth": {
                "revenue_growth_yoy_pct": revenue_growth,
                "earnings_growth_yoy_pct": _safe_float((info.get("earningsGrowth") or 0) * 100),
                "revenue_growth_quarterly_pct": _safe_float(
                    (info.get("revenueGrowth") or 0) * 100
                ),
                "net_income_growth_yoy_pct": net_income_growth,
                "eps_trend_last4q": eps_trend,
            },
            "balance_sheet": {
                "debt_to_equity": _safe_float(info.get("debtToEquity")),
                "current_ratio": _safe_float(info.get("currentRatio")),
                "quick_ratio": _safe_float(info.get("quickRatio")),
                "total_cash_cr": _safe_float(
                    (info.get("totalCash") or 0) / 1e7
                ),
                "total_debt_cr": _safe_float(
                    (info.get("totalDebt") or 0) / 1e7
                ),
            },
            "dividends": {
                "dividend_yield_pct": _safe_float((info.get("dividendYield") or 0) * 100),
                "payout_ratio": _safe_float(info.get("payoutRatio")),
            },
            "analyst_consensus": {
                "recommendation": info.get("recommendationKey", "N/A"),
                "target_mean_price": _safe_float(info.get("targetMeanPrice")),
                "number_of_analyst_opinions": info.get("numberOfAnalystOpinions"),
            },
        }
        return json.dumps(result, default=str)

    except Exception as exc:
        return json.dumps({"error": f"Financials fetch failed for {symbol}: {exc}"})


# ---------------------------------------------------------------------------
# Tool 3 – Peer Comparison
# ---------------------------------------------------------------------------

@mcp.tool()
def get_peer_comparison(symbol: str, peers: list[str] | None = None) -> str:
    """
    Fetch and compare key metrics for the target stock vs. peer companies.

    Args:
        symbol: Primary NSE ticker e.g. 'RELIANCE.NS'
        peers: List of peer NSE tickers e.g. ['ONGC.NS', 'BPCL.NS']

    Returns:
        JSON string with side-by-side comparison table.
    """
    if peers is None:
        peers = []

    all_symbols = [symbol] + [p for p in peers if p != symbol]
    comparison = []

    for sym in all_symbols:
        try:
            t, info = _safe_ticker(sym)
            comparison.append({
                "symbol": sym,
                "name": info.get("longName", sym),
                "market_cap_cr": _safe_float((info.get("marketCap") or 0) / 1e7),
                "trailing_pe": _safe_float(info.get("trailingPE")),
                "price_to_book": _safe_float(info.get("priceToBook")),
                "net_margin_pct": _safe_float((info.get("profitMargins") or 0) * 100),
                "roe_pct": _safe_float((info.get("returnOnEquity") or 0) * 100),
                "revenue_growth_pct": _safe_float((info.get("revenueGrowth") or 0) * 100),
                "debt_to_equity": _safe_float(info.get("debtToEquity")),
                "dividend_yield_pct": _safe_float((info.get("dividendYield") or 0) * 100),
                "52w_high": _safe_float(info.get("fiftyTwoWeekHigh")),
                "52w_low": _safe_float(info.get("fiftyTwoWeekLow")),
            })
        except Exception as exc:
            comparison.append({"symbol": sym, "error": str(exc)})

    # Rank peers on key metrics (lower rank = better)
    df = pd.DataFrame(comparison)
    rankings = {}
    for metric in ["trailing_pe", "price_to_book", "debt_to_equity"]:
        if metric in df.columns:
            rankings[f"{metric}_rank"] = (
                df[metric].rank(method="min", na_option="bottom").astype(int).tolist()
            )
    for metric in ["net_margin_pct", "roe_pct", "revenue_growth_pct"]:
        if metric in df.columns:
            rankings[f"{metric}_rank"] = (
                df[metric].rank(ascending=False, method="min", na_option="bottom")
                          .astype(int).tolist()
            )

    return json.dumps({
        "primary_symbol": symbol,
        "peers_compared": peers,
        "comparison_table": comparison,
        "rankings_note": (
            "For valuation metrics (PE, PB, DE) lower rank = better. "
            "For profitability/growth metrics higher is better (rank 1 = best)."
        ),
        "rankings": rankings,
    }, default=str)


# ---------------------------------------------------------------------------
# Tool 4 – Recent News (yfinance + graceful mock fallback)
# ---------------------------------------------------------------------------

@mcp.tool()
def get_recent_news(symbol: str) -> str:
    """
    Fetch recent news headlines for a stock symbol.

    Uses yfinance's news feed. If unavailable, returns a clearly-labelled
    mock response so the pipeline can still complete.

    Args:
        symbol: NSE ticker e.g. 'INFY.NS'

    Returns:
        JSON string with list of news items (title, publisher, timestamp, link).
    """
    try:
        ticker = yf.Ticker(symbol)
        news_raw = ticker.news or []

        if news_raw:
            news_items = []
            for item in news_raw[:10]:
                # yfinance 0.2+ returns nested content objects
                content = item.get("content", item)
                title = (
                    content.get("title")
                    or item.get("title", "No title")
                )
                publisher = (
                    content.get("provider", {}).get("displayName")
                    or item.get("publisher", "Unknown")
                )
                pub_time = (
                    content.get("pubDate")
                    or item.get("providerPublishTime", "")
                )
                link = (
                    content.get("canonicalUrl", {}).get("url")
                    or item.get("link", "")
                )
                news_items.append({
                    "title": title,
                    "publisher": publisher,
                    "published_at": pub_time,
                    "link": link,
                })

        return json.dumps({
            "symbol": symbol,
            "source": "yfinance",
            "count": len(news_items) if 'news_items' in locals() else 0,
            "news": news_items if 'news_items' in locals() else [],
        })

    except Exception as exc:
        return json.dumps({
            "symbol": symbol,
            "error": str(exc),
            "news": [],
        })


# ---------------------------------------------------------------------------
# Tool 5 – Macro Indicators (sector-level lookup table + RBI data)
# ---------------------------------------------------------------------------

MACRO_DATA = {
    "Technology": {
        "rbi_repo_rate_pct": 6.5,
        "cpi_inflation_pct": 4.75,
        "gdp_growth_pct": 6.8,
        "sector_index": "Nifty IT",
        "sector_trend_6m": "sideways",
        "usd_inr": 83.8,
        "key_risks": ["USD/INR volatility (IT earns in USD)", "Global tech slowdown", "Visa policy changes"],
        "key_tailwinds": ["AI adoption driving demand", "Digital transformation spend", "Cloud migration"],
        "interest_rate_sensitivity": "low",
        "commentary": (
            "IT sector in India is relatively insulated from domestic rate changes as revenue is "
            "export-driven. Key watch: US Federal Reserve rate trajectory, deal wins, and attrition rates."
        ),
    },
    "Energy": {
        "rbi_repo_rate_pct": 6.5,
        "cpi_inflation_pct": 4.75,
        "gdp_growth_pct": 6.8,
        "sector_index": "Nifty Energy",
        "sector_trend_6m": "bullish",
        "crude_oil_usd": 78.5,
        "key_risks": ["Crude price volatility", "Subsidy burden on PSU refiners", "Global demand slowdown"],
        "key_tailwinds": ["India refinery expansion", "Petrochemical diversification", "Domestic fuel demand growth"],
        "interest_rate_sensitivity": "medium",
        "commentary": (
            "Energy sector benefits from India's growing fuel demand but faces headwinds from crude "
            "price volatility and government price regulation for PSU companies."
        ),
    },
    "Banking": {
        "rbi_repo_rate_pct": 6.5,
        "cpi_inflation_pct": 4.75,
        "gdp_growth_pct": 6.8,
        "sector_index": "Nifty Bank",
        "sector_trend_6m": "bullish",
        "key_risks": ["Rising NPAs in unsecured loans", "RBI regulatory tightening", "Credit cost normalization"],
        "key_tailwinds": ["Strong credit growth", "Low NPA levels at large banks", "Digital banking adoption"],
        "interest_rate_sensitivity": "high",
        "commentary": (
            "Banking NII (Net Interest Income) is directly impacted by RBI repo rate. In a rate-cut "
            "cycle, margins compress but loan growth typically accelerates. Watch: NPA trajectory and CASA ratio."
        ),
    },
    "Consumer": {
        "rbi_repo_rate_pct": 6.5,
        "cpi_inflation_pct": 4.75,
        "gdp_growth_pct": 6.8,
        "sector_index": "Nifty FMCG",
        "sector_trend_6m": "sideways",
        "key_risks": ["Rural consumption slowdown", "Input cost inflation", "Competition from D2C brands"],
        "key_tailwinds": ["Premiumization trend", "Rising middle-class income", "Urban consumption resilience"],
        "interest_rate_sensitivity": "low",
        "commentary": (
            "FMCG companies benefit from volume-driven growth. Watch: rural vs. urban consumption divergence, "
            "commodity prices (palm oil, crude derivatives), and market share trends."
        ),
    },
    "Pharmaceuticals": {
        "rbi_repo_rate_pct": 6.5,
        "cpi_inflation_pct": 4.75,
        "gdp_growth_pct": 6.8,
        "sector_index": "Nifty Pharma",
        "sector_trend_6m": "bullish",
        "key_risks": ["US FDA compliance issues", "Price erosion in US generics", "INR appreciation"],
        "key_tailwinds": ["Strong domestic branded formulations", "CDMO opportunity", "Biosimilars pipeline"],
        "interest_rate_sensitivity": "low",
        "commentary": (
            "Indian pharma has strong export revenue (US generics, emerging markets). "
            "Key watch: USFDA inspection outcomes, US pricing environment, API supply chain."
        ),
    },
    "Unknown": {
        "rbi_repo_rate_pct": 6.5,
        "cpi_inflation_pct": 4.75,
        "gdp_growth_pct": 6.8,
        "sector_index": "Nifty 50",
        "sector_trend_6m": "sideways",
        "key_risks": ["Global macro headwinds", "Domestic inflation", "Geopolitical uncertainty"],
        "key_tailwinds": ["India growth story", "Government capex push", "FII/DII inflows"],
        "interest_rate_sensitivity": "medium",
        "commentary": (
            "India remains a structural growth story. Current macro backdrop: RBI in rate-cut mode, "
            "inflation within target band, GDP growth above 6.5%."
        ),
    },
}

# Aliases for sector names that yfinance might return
SECTOR_ALIASES = {
    "information technology": "Technology",
    "technology": "Technology",
    "it": "Technology",
    "software": "Technology",
    "oil & gas": "Energy",
    "oil and gas": "Energy",
    "energy": "Energy",
    "petroleum": "Energy",
    "financial services": "Banking",
    "banks": "Banking",
    "banking": "Banking",
    "financials": "Banking",
    "consumer staples": "Consumer",
    "consumer goods": "Consumer",
    "fmcg": "Consumer",
    "healthcare": "Pharmaceuticals",
    "pharma": "Pharmaceuticals",
    "pharmaceuticals": "Pharmaceuticals",
    "biotechnology": "Pharmaceuticals",
}


@mcp.tool()
def get_macro_indicators(sector: str) -> str:
    """
    Return macro-economic context relevant to the given sector.

    Args:
        sector: Sector name e.g. 'Technology', 'Energy', 'Banking'

    Returns:
        JSON string with RBI rate, inflation, sector trend, risks, tailwinds.
    """
    try:
        normalized = SECTOR_ALIASES.get(sector.lower(), sector)
        data = MACRO_DATA.get(normalized, MACRO_DATA["Unknown"]).copy()
        data["queried_sector"] = sector
        data["normalized_sector"] = normalized
        data["as_of"] = "2025-Q1 (structured reference data — not real-time)"
        return json.dumps(data)
    except Exception as exc:
        return json.dumps({"error": f"Macro lookup failed for sector '{sector}': {exc}"})



@mcp.tool()
def save_audit_log(
    verdict: str,
    reason: str,
    final_card: str,
    symbol: str = "UNKNOWN",
) -> str:
    """
    Save the compliance review result to a local JSON audit log file.

    Args:
        verdict: 'PASS' or 'FAIL'
        reason: Explanation of compliance decision and any rewrites made
        final_card: The compliant (possibly rewritten) research card
        symbol: The stock symbol being analysed (for traceability)

    Returns:
        Confirmation string with log file path.
    """
    import os
    from datetime import datetime
    
    audit_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "audit_log.json",
    )
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "symbol": symbol,
        "verdict": verdict,
        "reason": reason,
        "final_card_preview": final_card[:500] + "..." if len(final_card) > 500 else final_card,
        "full_card_length": len(final_card),
    }

    logs = []
    if os.path.exists(audit_path):
        try:
            with open(audit_path, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except (json.JSONDecodeError, OSError):
            logs = []

    logs.append(log_entry)

    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

    return f"Audit log saved to {audit_path} (entry {len(logs)} of {len(logs)} total)."


# ---------------------------------------------------------------------------
# Entry point — run as standalone MCP server (stdio transport)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    print("Starting EquiSage Market Data MCP Server (stdio)...", file=sys.stderr, flush=True)
    mcp.run()
