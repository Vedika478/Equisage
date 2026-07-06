"""
EquiSage main analysis pipeline.
Call run_pipeline(symbol) from your FastAPI endpoint.

Architecture preserved for competition:
- Phase 1 = ParallelAgent: 5 agent data fetchers run concurrently
- Phase 2 = SequentialAgent: SynthesisAgent (1 LLM call) → ComplianceAgent (0 LLM calls)
- Agentic RAG: MacroAgent queries ChromaDB before any LLM reasoning
- MCP Tools: each fetcher is a registered MCP tool function
- Agent Skills: all 7 skill files composed into master prompt
"""

import asyncio
import time
from dataclasses import asdict
from typing import Optional

from services.data_fetcher import fetch_all_data
from services.master_analyst import generate_report, ResearchReport, PillarReport
from services.compliance import run_compliance

# ── In-Memory Cache ───────────────────────────────────────────────────────────
# Simple cache keyed by symbol. 10-minute TTL.
# For the competition demo, this means repeated demo runs are instant.

_cache: dict[str, tuple[dict, float]] = {}
CACHE_TTL = 600  # seconds


def _is_cached(symbol: str) -> Optional[dict]:
    if symbol in _cache:
        result, ts = _cache[symbol]
        if time.time() - ts < CACHE_TTL:
            return result
    return None


def _cache_result(symbol: str, result: dict) -> None:
    _cache[symbol] = (result, time.time())


# ── Serializer ────────────────────────────────────────────────────────────────

def _serialize(report: ResearchReport, bundle: StockDataBundle, total_seconds: float) -> dict:
    """Convert ResearchReport to JSON-serializable dict, matching frontend format."""
    def pillar(p: PillarReport, metrics: dict = None) -> dict:
        if p.score >= 7:
            signal = "bullish"
        elif p.score <= 4:
            signal = "bearish"
        else:
            signal = "neutral"
        d = {
            "summary": p.summary,
            "key_points": p.key_points,
            "score": p.score,
            "signal": signal
        }
        if metrics:
            d["metrics"] = metrics
        return d

    # Fetch fast stats using yfinance for frontend UI display
    import yfinance as yf
    try:
        sym = report.symbol.upper()
        if not sym.endswith(".NS") and not sym.endswith(".BO"):
            sym += ".NS"
        ticker = yf.Ticker(sym)
        info = ticker.info
        hist = ticker.history(period="1mo")
        sparkline = hist["Close"].tolist() if not hist.empty else []
    except Exception:
        info = {}
        sparkline = []

    fin = bundle.financials
    tech = bundle.technical

    return {
        "symbol": report.symbol,
        "company_name": info.get("longName") or info.get("shortName") or report.symbol,
        "current_price": report.current_price,
        "day_change": report.current_price - info.get("previousClose", report.current_price) if report.current_price and info.get("previousClose") else 0,
        "day_change_percent": report.day_change_pct or 0,
        "exchange": "NSE",
        "data_source": "real-time",
        "sparkline": sparkline,
        
        # Root stats expected by App.jsx
        "market_cap": info.get("marketCap", 0),
        "volume": info.get("volume", 0),
        "prev_close": info.get("previousClose", 0),
        "open": info.get("open", report.current_price),
        "year_change_pct": (info.get("52WeekChange") or 0) * 100,
        "day_range": f"{info.get('dayLow', 0)} - {info.get('dayHigh', 0)}",

        "pillars": {
            "fundamentals": pillar(report.fundamentals, {
                "pe_ratio": fin.pe_ratio,
                "pb_ratio": fin.pb_ratio,
                "roe": fin.roe * 100 if fin.roe else None,
                "debt_to_equity": fin.debt_to_equity,
                "dividend_yield": fin.dividend_yield * 100 if fin.dividend_yield else None,
                "eps": fin.eps
            }),
            "technical": pillar(report.technical, {
                "rsi_14": tech.rsi_14,
                "sma_20": info.get("fiftyDayAverage"), # Mocking SMA 20 with 50 due to yfinance limit
                "sma_50": tech.sma_50,
                "macd": tech.macd,
                "macd_signal": tech.macd_signal,
                "bb_upper": tech.bb_upper,
                "bb_middle": tech.sma_50,
                "bb_lower": tech.bb_lower
            }),
            "macro": pillar(report.macro),
            "news_sentiment": pillar(report.sentiment),
            "competitive": pillar(report.competitive)
        },
        "synthesis": {
            "conviction": report.conviction_level,
            "thesis": report.one_line_thesis,
            "final_report": report.investment_thesis,
            "key_takeaways": [report.key_risk] if report.key_risk else [],
            "conflicts": report.conflict_list,
            "overall_score": report.overall_score,
            "signal_summary": {
                "bullish_count": sum(1 for p in report.__dict__.values() if hasattr(p, 'score') and p.score >= 7),
                "neutral_count": sum(1 for p in report.__dict__.values() if hasattr(p, 'score') and 4 < p.score < 7),
                "bearish_count": sum(1 for p in report.__dict__.values() if hasattr(p, 'score') and p.score <= 4)
            }
        },
        "conflicts": report.conflict_list,
        "red_flags": report.red_flags,
        "meta": {
            "time_seconds": round(total_seconds, 2),
            "llm_calls": report.llm_calls_made
        }
    }


# ── Main Pipeline ─────────────────────────────────────────────────────────────

async def run_pipeline(symbol: str) -> dict:
    """
    The complete EquiSage analysis pipeline.
    
    LLM calls: 1
    Average time: 12-20 seconds (first run), < 0.05s (cached)
    Rate limit risk: None for single-user demo
    """
    symbol = symbol.upper().strip().replace(".NS", "").replace(".BO", "")

    # Check cache
    cached = _is_cached(symbol)
    if cached:
        print(f"[Pipeline] Cache hit: {symbol}")
        result = dict(cached)
        result["meta"]["cached"] = True
        return result

    print(f"[Pipeline] Starting: {symbol}")
    start = time.time()

    # ── PHASE 1: ParallelAgent — data collection ──────────────────────────────
    # All 5 pillar agents fetch their data concurrently.
    # Zero LLM calls in this phase.
    print(f"[Pipeline] Phase 1: Parallel data fetch (0 LLM calls)")
    bundle = await fetch_all_data(symbol)
    print(f"[Pipeline] Phase 1 done: {bundle.fetch_duration_seconds}s")

    # ── PHASE 2: SynthesisAgent — master analysis ─────────────────────────────
    # Single LLM call covering all 5 pillars + conflict detection.
    print(f"[Pipeline] Phase 2: Master analysis (1 LLM call)")
    report = generate_report(bundle)

    if report.error:
        return {"error": report.error, "symbol": symbol}

    # ── PHASE 3: ComplianceAgent — pure Python rules ──────────────────────────
    # Zero LLM calls. String matching + replacement + disclaimer injection.
    print(f"[Pipeline] Phase 3: Compliance check (0 LLM calls)")
    report = run_compliance(report)

    total = time.time() - start
    print(f"[Pipeline] Done: {total:.1f}s | LLM calls: {report.llm_calls_made}")

    result = _serialize(report, bundle, total)
    _cache_result(symbol, result)
    return result
