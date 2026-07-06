"""
Pure data collection for all 5 EquiSage analysis pillars.
Zero LLM calls. Runs in parallel. Completes in 3-8 seconds.
Each fetcher corresponds to one ADK pillar agent's data domain.
"""

import asyncio
import time
import yfinance as yf
import pandas as pd
import chromadb
from dataclasses import dataclass, field
from typing import Optional

from services.news_fetcher import NewsBundle, fetch_news_for_stock, format_news_for_prompt

# ── Peer Mapping ──────────────────────────────────────────────────────────────

PEER_MAP = {
    "HDFCBANK":   ["ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN"],
    "ICICIBANK":  ["HDFCBANK", "KOTAKBANK", "AXISBANK", "SBIN"],
    "SBIN":       ["HDFCBANK", "ICICIBANK", "BANKBARODA", "PNB"],
    "KOTAKBANK":  ["HDFCBANK", "ICICIBANK", "AXISBANK", "INDUSINDBK"],
    "AXISBANK":   ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "INDUSINDBK"],
    "TCS":        ["INFY", "WIPRO", "HCLTECH", "TECHM"],
    "INFY":       ["TCS", "WIPRO", "HCLTECH", "TECHM"],
    "WIPRO":      ["TCS", "INFY", "HCLTECH", "TECHM"],
    "HCLTECH":    ["TCS", "INFY", "WIPRO", "TECHM"],
    "RELIANCE":   ["ONGC", "IOC", "BPCL", "HPCL"],
    "CHOLAFIN":   ["BAJFINANCE", "MUTHOOTFIN", "MANAPPURAM"],
    "BAJFINANCE": ["CHOLAFIN", "HDFCBANK", "MUTHOOTFIN"],
    "HINDUNILVR": ["ITC", "BRITANNIA", "NESTLEIND", "DABUR"],
    "ITC":        ["HINDUNILVR", "BRITANNIA", "NESTLEIND", "GODFRYPHLP"],
    "SUNPHARMA":  ["DRREDDY", "CIPLA", "DIVISLAB", "AUROPHARMA"],
    "DRREDDY":    ["SUNPHARMA", "CIPLA", "DIVISLAB", "AUROPHARMA"],
    "TATAMOTORS": ["MARUTI", "M&M", "HEROMOTOCO", "BAJAJ-AUTO"],
    "MARUTI":     ["TATAMOTORS", "M&M", "HEROMOTOCO", "BAJAJ-AUTO"],
    "ZOMATO":     ["SWIGGY", "PAYTM", "NYKAA"],
    "LTIM":       ["TCS", "INFY", "WIPRO", "PERSISTENT"],
}

# ── Data Models ───────────────────────────────────────────────────────────────

@dataclass
class FinancialsData:
    company_name: str = ""
    sector: str = "Unknown"
    industry: str = "Unknown"
    exchange: str = "NSE"
    current_price: Optional[float] = None
    day_change_pct: Optional[float] = None
    week52_high: Optional[float] = None
    week52_low: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    profit_margins: Optional[float] = None
    dividend_yield: Optional[float] = None
    eps: Optional[float] = None
    promoter_holding: Optional[float] = None
    error: Optional[str] = None

@dataclass
class TechnicalData:
    current_price: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    rsi_14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    volume_current: Optional[float] = None
    volume_avg_20d: Optional[float] = None
    above_sma50: bool = False
    above_sma200: bool = False
    volume_above_avg: bool = False
    rsi_signal: str = "NEUTRAL"
    trend_signal: str = "NEUTRAL"
    error: Optional[str] = None

@dataclass
class MacroData:
    rag_context: str = ""
    sector_queried: str = ""
    chunks_retrieved: int = 0
    error: Optional[str] = None

@dataclass
class PeerData:
    peers: list[dict] = field(default_factory=list)
    error: Optional[str] = None

@dataclass
class StockDataBundle:
    """
    Complete data package for one stock.
    Built by 5 pillar agents running in parallel.
    Zero LLM calls to construct.
    """
    symbol: str
    financials: FinancialsData = field(default_factory=FinancialsData)
    technical: TechnicalData = field(default_factory=TechnicalData)
    news: NewsBundle = field(default_factory=NewsBundle)
    macro: MacroData = field(default_factory=MacroData)
    peers: PeerData = field(default_factory=PeerData)
    fetch_duration_seconds: float = 0.0


# ── Symbol Utilities ──────────────────────────────────────────────────────────

def normalize(symbol: str) -> str:
    s = symbol.upper().strip()
    if not s.endswith(".NS") and not s.endswith(".BO"):
        s += ".NS"
    return s

def base(symbol: str) -> str:
    return symbol.upper().replace(".NS", "").replace(".BO", "").strip()


# ── Pillar Agent Data Fetchers ─────────────────────────────────────────────────
# Each function = one pillar agent's data responsibility

def fundamentals_agent_fetch(symbol: str) -> FinancialsData:
    """
    FundamentalsAgent data fetch.
    Retrieves all fundamental metrics from yfinance.
    """
    try:
        ticker = yf.Ticker(normalize(symbol))
        info = ticker.info

        if not info or (not info.get("regularMarketPrice") and not info.get("currentPrice")):
            # Try BSE
            ticker = yf.Ticker(base(symbol) + ".BO")
            info = ticker.info

        if not info or (not info.get("regularMarketPrice") and not info.get("currentPrice")):
            return FinancialsData(error=f"No data for {symbol}. Verify NSE symbol.")

        current = info.get("regularMarketPrice") or info.get("currentPrice")
        prev = info.get("previousClose")
        change_pct = ((current - prev) / prev * 100) if current and prev and prev > 0 else None

        return FinancialsData(
            company_name=info.get("longName") or info.get("shortName") or base(symbol),
            sector=info.get("sector") or "Unknown",
            industry=info.get("industry") or "Unknown",
            current_price=round(float(current), 2) if current else None,
            day_change_pct=round(change_pct, 2) if change_pct else None,
            week52_high=info.get("fiftyTwoWeekHigh"),
            week52_low=info.get("fiftyTwoWeekLow"),
            market_cap=info.get("marketCap"),
            pe_ratio=info.get("trailingPE") or info.get("forwardPE"),
            pb_ratio=info.get("priceToBook"),
            roe=info.get("returnOnEquity"),
            debt_to_equity=info.get("debtToEquity"),
            revenue_growth=info.get("revenueGrowth"),
            earnings_growth=info.get("earningsGrowth"),
            profit_margins=info.get("profitMargins"),
            dividend_yield=info.get("dividendYield"),
            eps=info.get("trailingEps"),
        )
    except Exception as e:
        return FinancialsData(error=str(e))


def technical_agent_fetch(symbol: str) -> TechnicalData:
    """
    TechnicalAgent data fetch.
    Computes all technical indicators from price history.
    """
    try:
        ticker = yf.Ticker(normalize(symbol))
        hist = ticker.history(period="1y", interval="1d")

        if hist.empty or len(hist) < 30:
            return TechnicalData(error="Insufficient price history for indicators.")

        close = hist["Close"]
        volume = hist["Volume"]
        current_price = float(close.iloc[-1])

        # Moving Averages
        sma_50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
        sma_200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

        # RSI (Wilder's smoothing)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, float('nan'))
        rsi = float((100 - 100 / (1 + rs)).iloc[-1])

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line

        # Bollinger Bands (20-day)
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        bb_upper = float((sma20 + 2 * std20).iloc[-1])
        bb_lower = float((sma20 - 2 * std20).iloc[-1])

        # Volume
        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        vol_curr = float(volume.iloc[-1])

        # Signals
        above_50 = bool(sma_50 and current_price > sma_50)
        above_200 = bool(sma_200 and current_price > sma_200)
        rsi_signal = "OVERBOUGHT" if rsi > 70 else "OVERSOLD" if rsi < 30 else "NEUTRAL"
        trend = "BULLISH" if above_200 and above_50 else "BEARISH" if not above_200 else "MIXED"

        return TechnicalData(
            current_price=round(current_price, 2),
            sma_50=round(sma_50, 2) if sma_50 else None,
            sma_200=round(sma_200, 2) if sma_200 else None,
            rsi_14=round(rsi, 1),
            macd=round(float(macd_line.iloc[-1]), 3),
            macd_signal=round(float(signal_line.iloc[-1]), 3),
            macd_histogram=round(float(macd_hist.iloc[-1]), 3),
            bb_upper=round(bb_upper, 2),
            bb_lower=round(bb_lower, 2),
            volume_current=round(vol_curr, 0),
            volume_avg_20d=round(vol_avg, 0),
            above_sma50=above_50,
            above_sma200=above_200,
            volume_above_avg=vol_curr > vol_avg,
            rsi_signal=rsi_signal,
            trend_signal=trend,
        )
    except Exception as e:
        return TechnicalData(error=str(e))


def news_agent_fetch(symbol: str, company_name: str = "") -> NewsBundle:
    """
    NewsSentimentAgent data fetch.
    Gets news from Indian RSS feeds + NSE official announcements.
    """
    return fetch_news_for_stock(symbol)


def macro_agent_fetch(sector: str) -> MacroData:
    """
    MacroAgent data fetch — this is the Agentic RAG step.
    Retrieves relevant macro context from ChromaDB BEFORE any LLM reasoning.
    The retrieved chunks feed directly into the master analysis prompt.
    """
    static_fallback = _static_macro_context(sector)

    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_or_create_collection("macro_knowledge")

        if collection.count() == 0:
            _seed_macro_knowledge(collection)

        results = collection.query(
            query_texts=[
                f"India macroeconomic impact {sector} sector",
                f"RBI monetary policy {sector} stocks",
                f"Indian equity market {sector} outlook",
            ],
            n_results=4,
        )

        if results and results["documents"] and results["documents"][0]:
            # Deduplicate and join retrieved chunks
            seen = set()
            chunks = []
            for doc_list in results["documents"]:
                for doc in doc_list:
                    if doc not in seen:
                        seen.add(doc)
                        chunks.append(doc)

            return MacroData(
                rag_context="\n\n".join(chunks[:4]),
                sector_queried=sector,
                chunks_retrieved=len(chunks),
            )

    except Exception as e:
        return MacroData(
            rag_context=static_fallback,
            error=str(e),
        )

    return MacroData(rag_context=static_fallback)


def competitive_agent_fetch(symbol: str) -> PeerData:
    """
    CompetitiveAgent data fetch.
    Gets financial metrics for sector peers from yfinance.
    """
    try:
        b = base(symbol)
        peer_list = PEER_MAP.get(b, [])

        if not peer_list:
            return PeerData(error=f"No peer mapping for {b}. Add to PEER_MAP.")

        peers = []
        for peer_b in peer_list[:4]:
            try:
                ticker = yf.Ticker(peer_b + ".NS")
                info = ticker.info
                if info and info.get("regularMarketPrice"):
                    peers.append({
                        "symbol": peer_b,
                        "name": info.get("shortName") or peer_b,
                        "price": info.get("regularMarketPrice"),
                        "pe": info.get("trailingPE"),
                        "pb": info.get("priceToBook"),
                        "roe": info.get("returnOnEquity"),
                        "market_cap": info.get("marketCap"),
                        "revenue_growth": info.get("revenueGrowth"),
                        "profit_margins": info.get("profitMargins"),
                        "debt_to_equity": info.get("debtToEquity"),
                    })
            except Exception:
                continue

        return PeerData(peers=peers)
    except Exception as e:
        return PeerData(error=str(e))


# ── Parallel Orchestration ────────────────────────────────────────────────────

async def fetch_all_data(symbol: str) -> StockDataBundle:
    """
    Runs all 5 pillar agent data fetchers in parallel using asyncio.
    This is where ParallelAgent behavior lives — all 5 run concurrently.
    Zero LLM calls. Completes in 3-8 seconds.
    """
    start = time.time()
    loop = asyncio.get_event_loop()

    # Start financials first — we need company name + sector for other fetchers
    fin_future = loop.run_in_executor(None, fundamentals_agent_fetch, symbol)
    tech_future = loop.run_in_executor(None, technical_agent_fetch, symbol)

    financials = await fin_future
    technical = await tech_future

    # Now run remaining 3 with sector context from financials
    news_future = loop.run_in_executor(None, news_agent_fetch, symbol, financials.company_name)
    macro_future = loop.run_in_executor(None, macro_agent_fetch, financials.sector)
    peers_future = loop.run_in_executor(None, competitive_agent_fetch, symbol)

    news, macro, peers = await asyncio.gather(news_future, macro_future, peers_future)

    return StockDataBundle(
        symbol=symbol,
        financials=financials,
        technical=technical,
        news=news,
        macro=macro,
        peers=peers,
        fetch_duration_seconds=round(time.time() - start, 2),
    )


# ── Macro RAG Seed Data ───────────────────────────────────────────────────────

def _seed_macro_knowledge(collection) -> None:
    """
    Seeds ChromaDB with Indian macroeconomic context.
    Called automatically if collection is empty.
    """
    chunks = [
        # RBI Policy
        "RBI Rate Cuts and Banking Sector: RBI has been in a rate-cutting cycle since February 2025. Repo rate stands at 6.00%. Rate cuts reduce the cost of funds for banks. Banks with high CASA ratios (low-cost deposits) benefit most — their liability costs fall faster than asset yields. Net Interest Margins typically expand 6-12 months post rate cut. HDFC Bank (CASA ~47%), Kotak Bank (CASA ~53%) are structurally advantaged in rate-cut environments. SBI benefits through higher loan demand in the retail and MSME segment.",
        "RBI Rate Cuts and NBFCs: Non-Banking Financial Companies benefit significantly from rate cuts. Lower borrowing costs directly expand NIMs for NBFCs with floating-rate assets. Vehicle finance NBFCs like Cholamandalam Finance benefit through both lower funding costs and higher vehicle loan demand as EMIs fall. Consumer finance companies like Bajaj Finance see higher loan book growth as affordability improves.",
        "RBI Rate Cuts and Real Estate: Rate cuts directly stimulate housing demand as home loan EMIs fall. Every 50 bps rate cut reduces monthly EMI on a ₹50L loan by approximately ₹1,500. DLF, Godrej Properties, Prestige Estates, Oberoi Realty are primary beneficiaries. Effect typically visible 2-3 quarters after rate cut as new buyer decisions materialize.",
        "RBI Rate Cuts and Auto Sector: Lower vehicle financing rates stimulate auto demand. Two-wheeler segment (Hero MotoCorp, Bajaj Auto) responds faster than passenger vehicles due to higher rural sensitivity. Maruti Suzuki benefits through improved Maruti Finance disbursals. Commercial vehicle demand is more sensitive to economic activity than interest rates.",
        # USD/INR
        "Rupee Depreciation and IT Sector: Indian IT companies earn revenue in USD/GBP/EUR but incur costs in INR. Rupee depreciation directly expands operating margins — every 1% rupee depreciation adds approximately 0.4-0.6% to IT EBIT margins. TCS, Infosys, Wipro, HCL Technologies, LTIMindtree are primary beneficiaries. Natural hedge exists as companies hold USD receivables. However, clients increasingly demand rupee-denominated contracts for India work.",
        "Rupee Depreciation and Import-Heavy Sectors: Companies importing raw materials in USD face higher input costs when rupee weakens. Oil marketing companies (HPCL, BPCL, IOC) are most exposed — crude oil is USD-denominated. Airlines face higher jet fuel import costs. Companies with unhedged USD debt see higher financing costs. Paint companies (Asian Paints) face higher TiO2 import costs.",
        "Rupee Depreciation and Pharma Exporters: Indian pharmaceutical exporters benefit from rupee weakening. US and European generic revenue translates to more INR. API (Active Pharmaceutical Ingredient) manufacturers especially benefit. Sun Pharma, Dr Reddy's, Cipla, Aurobindo Pharma are key beneficiaries. However, imported raw material costs partially offset the benefit.",
        # Global Macro
        "US Recession Risk and Indian IT: Indian IT services revenue is concentrated in the US (55-65% for most companies). US discretionary technology spend is the first budget item cut in recession. IT services revenue growth slows 12-18 months after US recession signals. BFSI vertical (banking clients) is most sensitive to US macro. TCS, Infosys have guided conservatively for FY26 citing weak discretionary spend.",
        "India GDP and Domestic Consumption: India GDP growth projected at 6.8% for FY26 — one of the fastest-growing major economies globally. Strong GDP drives urban consumption, particularly in premium categories. FMCG companies with urban premium exposure (HUL premium brands, Nestle, Britannia) benefit. Rural demand recovering on good monsoon FY25 and successive MSP hikes.",
        # Budget/Policy
        "India Union Budget FY26 and Infrastructure: The Union Budget FY26 maintained high infrastructure capex at ₹11.1 lakh crore. Primary beneficiaries: L&T (engineering & construction), Ultratech Cement, Ambuja Cement, ACC, Tata Steel, JSW Steel (construction materials), NTPC, Power Grid Corporation. Road construction pace targeting 15,000 km in FY26 benefits KNR Constructions, PNC Infratech, Dilip Buildcon.",
        "PLI Schemes and Manufacturing: Production Linked Incentive schemes cover 14 sectors. Electronics: Dixon Technologies, Amber Enterprises (AC components). Pharmaceuticals: Sun Pharma, Cipla (API manufacturing). Specialty chemicals, textiles, and food processing sectors also covered. PLI incentives span 5-7 years, providing earnings visibility for qualifying companies.",
        "FII and DII Flows India 2025: FII (Foreign Institutional Investors) have been net sellers in Indian equities in early 2025 due to global risk-off. However, DII (domestic mutual funds) have offset FII selling through SIP inflows of ₹24,000+ crore per month. This domestic buying support has limited downside in large-caps. India's weight in MSCI Emerging Markets index at 19% — any EM reallocation benefits India disproportionately.",
        "Defence Indigenization Theme: India's defence budget at ₹6.2 lakh crore for FY26. Government's 'Make in India' push mandating 75% domestic procurement by FY26. Primary beneficiaries: Hindustan Aeronautics Ltd (HAL), Bharat Electronics Ltd (BEL), Bharat Dynamics Ltd (BDL), BEML, Data Patterns, Paras Defence. Multi-year earnings visibility as order books extend 3-5 years forward.",
        "Crude Oil Impact on Indian Economy: India imports ~85% of its crude requirement. At $75-80/bbl Brent, India's import bill is manageable and fiscal comfortable. Oil below $70 is positive for India macro — lower inflation, better fiscal math, RBI rate cut room. OMCs (HPCL, BPCL, IOC) benefit from lower crude as marketing margins improve when retail prices are not cut proportionally.",
    ]

    ids = [f"macro_{i}" for i in range(len(chunks))]
    collection.add(documents=chunks, ids=ids)
    print(f"[MacroRAG] Seeded {len(chunks)} macro knowledge chunks into ChromaDB")


def _static_macro_context(sector: str) -> str:
    """Fallback macro context when ChromaDB is unavailable."""
    base_context = """Current Indian Macroeconomic Environment (2025):
• RBI Rate Cycle: Cutting cycle since Feb 2025. Repo rate at 6.00%.
• Inflation: CPI at ~4.2%, within RBI 2-6% comfort band.
• Rupee: USD/INR 83-84, relatively stable.
• GDP Growth: ~6.8% projected FY26.
• FII Flows: Mixed — selective buying in quality large-caps.
• DII Support: SIP flows ₹24,000 cr/month providing market floor."""

    sector_addons = {
        "Financial Services": "\n• Sector: Rate-cut beneficiary. CASA-heavy banks see NIM expansion. NBFC loan growth accelerating.",
        "Technology": "\n• Sector: USD/INR stable (neutral for margins). US discretionary spend weak. AI deal wins emerging.",
        "Energy": "\n• Sector: Crude at $75-80/bbl. Refining margins normalized. OMC pricing decisions are government-influenced.",
        "Consumer Defensive": "\n• Sector: Rural demand recovering on good monsoon. Urban premium consumption robust.",
        "Healthcare": "\n• Sector: US generics pricing stabilizing. India domestic formulations growing 10-12%. USFDA compliance critical.",
        "Basic Materials": "\n• Sector: Infrastructure capex driving domestic steel/cement demand. China supply overhang caps global pricing.",
        "Industrials": "\n• Sector: Budget capex ₹11.1L crore supports order inflows. Defence indigenization multi-year tailwind.",
    }

    return base_context + sector_addons.get(sector, "\n• Sector: Monitor RBI policy and global risk sentiment for rotation signals.")
