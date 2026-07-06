"""
EquiSage FastAPI Backend Server

Endpoints:
  POST /api/research   — Run full multi-agent analysis for a stock symbol
  GET  /api/popular    — List popular NSE/BSE stocks
  GET  /api/health     — Health check
"""

import asyncio
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

# Fix import paths
sys.path.insert(0, os.path.dirname(__file__))


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── In-memory cache ──────────────────────────────────────────────────────────
_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))  # 5 minutes

def _cache_get(symbol: str) -> Optional[Dict]:
    entry = _cache.get(symbol)
    if entry and (time.time() - entry["cached_at"]) < CACHE_TTL_SECONDS:
        return entry["data"]
    return None

def _cache_set(symbol: str, data: Dict):
    _cache[symbol] = {"data": data, "cached_at": time.time()}


# ── Popular stocks ───────────────────────────────────────────────────────────
POPULAR_STOCKS = [
    {"symbol": "RELIANCE.NS",  "name": "Reliance Industries",       "sector": "Energy / Telecom"},
    {"symbol": "TCS.NS",       "name": "Tata Consultancy Services", "sector": "IT Services"},
    {"symbol": "HDFCBANK.NS",  "name": "HDFC Bank",                 "sector": "Private Banking"},
    {"symbol": "INFY.NS",      "name": "Infosys",                   "sector": "IT Services"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank",                "sector": "Private Banking"},
    {"symbol": "HINDUNILVR.NS","name": "Hindustan Unilever",        "sector": "FMCG"},
    {"symbol": "SBIN.NS",      "name": "State Bank of India",       "sector": "Public Banking"},
    {"symbol": "BHARTIARTL.NS","name": "Bharti Airtel",             "sector": "Telecom"},
    {"symbol": "WIPRO.NS",     "name": "Wipro",                     "sector": "IT Services"},
    {"symbol": "CHOLAFIN.NS",  "name": "Cholamandalam Finance",     "sector": "NBFC"},
]


# ── Startup / shutdown ───────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise ChromaDB knowledge base on startup
    logger.info("Initialising ChromaDB knowledge base…")
    try:
        from rag.macro_rag import initialize_knowledge_base, get_collection_stats
        stats = get_collection_stats()
        if not stats.get("success") or stats.get("total_chunks", 0) == 0:
            result = initialize_knowledge_base()
            logger.info("ChromaDB init: %s", result)
        else:
            logger.info("ChromaDB already loaded: %d chunks", stats["total_chunks"])
    except Exception as exc:
        logger.warning("ChromaDB init failed (non-fatal): %s", exc)

    # (Removed legacy orchestrator pre-warm)
    logger.info("EquiSage backend ready ✓")
    yield
    logger.info("EquiSage backend shutting down")


# ── FastAPI app ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="EquiSage API",
    description="AI-powered equity research for Indian markets",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ── Request / Response models ────────────────────────────────────────────────
class ResearchRequest(BaseModel):
    symbol: str

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        v = v.strip().upper().strip('.')
        if not v:
            raise ValueError("Symbol cannot be empty")
        return v


# ── Endpoints ────────────────────────────────────────────────────────────────
from services.pipeline import run_pipeline

import requests as req

def auto_resolve_symbol(symbol: str) -> str:
    """If the user enters a company name instead of a ticker, resolve it to the closest NSE ticker."""
    s = symbol.upper().strip()
    if s.endswith(".NS") or s.endswith(".BO"):
        return s
    
    # Use Yahoo Finance search to resolve
    try:
        resp = req.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={"q": s, "quotesCount": 5, "newsCount": 0, "enableFuzzyQuery": True},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5
        )
        data = resp.json()
        for quote in data.get("quotes", []):
            sym = quote.get("symbol", "")
            qtype = quote.get("quoteType", "")
            if qtype == "EQUITY" and (sym.endswith(".NS") or sym.endswith(".BO")):
                return sym
    except Exception:
        pass
        
    # Fallback to appending .NS if search fails
    return s + ".NS"

@app.post("/analyze")
async def analyze(request: ResearchRequest):
    symbol = request.symbol
    
    # Automatically resolve company names like "Asian Paints" to "ASIANPAINT.NS"
    resolved_symbol = auto_resolve_symbol(symbol)
    
    try:
        result = await run_pipeline(resolved_symbol)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/quick-price/{symbol}")
async def quick_price(symbol: str):
    """Fast price fetch — no agents, no LLM."""
    import yfinance as yf
    try:
        ticker = yf.Ticker(symbol.upper() + ".NS")
        info = ticker.info
        price = info.get("regularMarketPrice")
        prev = info.get("previousClose")
        change = ((price - prev) / prev * 100) if price and prev else 0
        return {"symbol": symbol, "price": price, "change_pct": round(change, 2)}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))



@app.get("/api/search")
async def search_stocks(q: str = ""):
    """
    Search for NSE/BSE stocks by company name or ticker symbol.
    Returns matched NSE/BSE stocks from Yahoo Finance.
    User can type 'Zomato', 'Tata Motors', 'INFY' etc.
    """
    if not q or len(q.strip()) < 2:
        return {"results": []}
    try:
        import requests as req
        resp = req.get(
            "https://query2.finance.yahoo.com/v1/finance/search",
            params={
                "q": q.strip(),
                "lang": "en-US",
                "region": "IN",
                "quotesCount": 15,
                "newsCount": 0,
                "enableFuzzyQuery": True,
                "quotesQueryId": "tss_match_phrase_query",
            },
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5,
        )
        data = resp.json()
        results = []
        for quote in data.get("quotes", []):
            sym = quote.get("symbol", "")
            qtype = quote.get("quoteType", "")
            exchange = quote.get("exchDisp", "")
            # Only return Indian exchange stocks
            if qtype == "EQUITY" and (sym.endswith(".NS") or sym.endswith(".BO")):
                results.append({
                    "symbol": sym,
                    "name": quote.get("shortname") or quote.get("longname") or sym,
                    "exchange": "NSE" if sym.endswith(".NS") else "BSE",
                    "sector": quote.get("sector", ""),
                    "industry": quote.get("industry", ""),
                })
        # Deduplicate: prefer .NS over .BO for same base symbol
        seen_bases = set()
        deduped = []
        for r in results:
            base = r["symbol"].split(".")[0]
            if base not in seen_bases:
                seen_bases.add(base)
                deduped.append(r)
        return {"results": deduped}
    except Exception as exc:
        logger.warning("Stock search failed: %s", exc)
        return {"results": []}




@app.get("/api/health")
async def health():
    """Health check endpoint."""
    api_key_set = bool(os.getenv("GEMINI_API_KEY", ""))
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gemini_api_key_configured": api_key_set,
        "agents": [
            "fundamentals", "technical", "news_sentiment",
            "macro", "competitive", "synthesis", "compliance",
        ],
        "cache_entries": len(_cache),
    }


@app.delete("/api/cache")
async def clear_cache():
    """Clear the research cache (useful during development)."""
    _cache.clear()
    return {"status": "ok", "message": "Cache cleared"}


from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

# ── Dev entry point ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
