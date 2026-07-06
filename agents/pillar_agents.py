"""
Five Pillar Agents for EquiSage.

Each agent:
  1. Loads its domain skill (.md file) as context
  2. Fetches real-time data via the MCP server
  3. Calls Gemini 2.0 Flash for analysis
  4. Returns structured JSON matching the skill's output format

Agents: FundamentalsAgent, TechnicalAgent, NewsAgent, MacroAgent, CompetitiveAgent
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

# Add parent dir to path for imports when running as module
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from google_adk import generate_with_retry, parse_json_response
from tools.mcp_server import EquiSageMCPServer

logger = logging.getLogger(__name__)

SKILLS_DIR = os.path.join(os.path.dirname(__file__), "..", "skills")


def _load_skill(filename: str) -> str:
    """Load a skill markdown file."""
    path = os.path.join(SKILLS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _safe_json(result: dict, fallback_key: str) -> dict:
    """Return result if it's a dict, else wrap it."""
    if isinstance(result, dict):
        return result
    return {fallback_key: str(result)}


class BaseAgent:
    """Base class with shared MCP server."""

    def __init__(self):
        self.mcp = EquiSageMCPServer(use_mock=False)

    async def _call_gemini(self, system_prompt: str, user_data: str) -> Dict[str, Any]:
        """Build a concise prompt, call LLM, parse JSON response."""
        full_prompt = (
            f"{system_prompt}\n\n"
            f"STOCK DATA:\n{user_data}\n\n"
            "Respond with ONLY a valid JSON object. No markdown. No explanation. "
            "Start with { and end with }."
        )
        raw = await generate_with_retry(full_prompt)
        return parse_json_response(raw)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Fundamentals Agent
# ─────────────────────────────────────────────────────────────────────────────

class FundamentalsAgent(BaseAgent):
    """
    Evaluates financial health and valuation.
    Tools used: get_fundamentals, get_stock_price
    """

    NAME = "fundamentals"

    def __init__(self):
        super().__init__()
        self.skill = _load_skill("fundamentals_skill.md")

    async def analyze(self, symbol: str) -> Dict[str, Any]:
        start = time.time()
        logger.info("[FundamentalsAgent] Analyzing %s", symbol)
        try:
            # Fetch data
            fund_data = self.mcp.get_fundamentals(symbol)
            price_data = self.mcp.get_stock_price(symbol)

            data_str = json.dumps({
                "symbol": symbol,
                "fundamentals": fund_data.get("data", {}),
                "price_info": price_data.get("data", {}),
            }, indent=2)

            result = await self._call_gemini(self.skill, data_str)
            result["agent"] = self.NAME
            result["duration_ms"] = int((time.time() - start) * 1000)
            result["tools_called"] = ["get_fundamentals", "get_stock_price"]
            return result

        except Exception as exc:
            logger.error("[FundamentalsAgent] Error: %s", exc)
            return self._fallback(symbol, start, str(exc))

    def _fallback(self, symbol: str, start: float, error: str) -> Dict[str, Any]:
        fund = self.mcp.get_fundamentals(symbol).get("data", {})
        return {
            "pillar": "fundamentals",
            "score": 5,
            "signal": "neutral",
            "summary": f"Fundamentals data fetched for {symbol}. LLM analysis unavailable: {error[:100]}",
            "metrics": fund,
            "key_insights": ["Data retrieved but AI analysis failed"],
            "agent": self.NAME,
            "duration_ms": int((time.time() - start) * 1000),
            "tools_called": ["get_fundamentals", "get_stock_price"],
        }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Technical Agent
# ─────────────────────────────────────────────────────────────────────────────

class TechnicalAgent(BaseAgent):
    """
    Evaluates price momentum, trends, and chart patterns.
    Tools used: get_technical_indicators, get_stock_price
    """

    NAME = "technical"

    def __init__(self):
        super().__init__()
        self.skill = _load_skill("technical_skill.md")

    async def analyze(self, symbol: str) -> Dict[str, Any]:
        start = time.time()
        logger.info("[TechnicalAgent] Analyzing %s", symbol)
        try:
            tech_data = self.mcp.get_technical_indicators(symbol)
            price_data = self.mcp.get_stock_price(symbol)

            data_str = json.dumps({
                "symbol": symbol,
                "technical_indicators": tech_data.get("data", {}),
                "current_price": price_data.get("data", {}).get("current_price"),
            }, indent=2)

            result = await self._call_gemini(self.skill, data_str)
            result["agent"] = self.NAME
            result["duration_ms"] = int((time.time() - start) * 1000)
            result["tools_called"] = ["get_technical_indicators", "get_stock_price"]
            return result

        except Exception as exc:
            logger.error("[TechnicalAgent] Error: %s", exc)
            return self._fallback(symbol, start, str(exc))

    def _fallback(self, symbol: str, start: float, error: str) -> Dict[str, Any]:
        tech = self.mcp.get_technical_indicators(symbol).get("data", {})
        return {
            "pillar": "technical",
            "score": 5,
            "signal": "neutral",
            "summary": f"Technical data fetched for {symbol}. LLM analysis unavailable: {error[:100]}",
            "metrics": tech,
            "key_insights": ["Data retrieved but AI analysis failed"],
            "agent": self.NAME,
            "duration_ms": int((time.time() - start) * 1000),
            "tools_called": ["get_technical_indicators", "get_stock_price"],
        }


# ─────────────────────────────────────────────────────────────────────────────
# 3. News / Sentiment Agent
# ─────────────────────────────────────────────────────────────────────────────

class NewsAgent(BaseAgent):
    """
    Evaluates recent news headlines and market sentiment.
    Tool used: get_news (real yfinance news, no API key needed)
    """

    NAME = "news_sentiment"

    def __init__(self):
        super().__init__()
        self.skill = _load_skill("news_skill.md")

    async def analyze(self, symbol: str) -> Dict[str, Any]:
        start = time.time()
        logger.info("[NewsAgent] Analyzing %s", symbol)
        try:
            news_data = self.mcp.get_news(symbol, limit=7)

            data_str = json.dumps({
                "symbol": symbol,
                "news_articles": news_data.get("data", []),
                "news_source": news_data.get("source", "unknown"),
            }, indent=2)

            result = await self._call_gemini(self.skill, data_str)
            result["agent"] = self.NAME
            result["duration_ms"] = int((time.time() - start) * 1000)
            result["tools_called"] = ["get_news"]
            return result

        except Exception as exc:
            logger.error("[NewsAgent] Error: %s", exc)
            return self._fallback(symbol, start, str(exc))

    def _fallback(self, symbol: str, start: float, error: str) -> Dict[str, Any]:
        news = self.mcp.get_news(symbol).get("data", [])
        return {
            "pillar": "news_sentiment",
            "score": 5,
            "signal": "neutral",
            "summary": f"News data fetched for {symbol}. LLM analysis unavailable: {error[:100]}",
            "news_count": len(news),
            "sentiment_breakdown": {"positive": 0, "neutral": len(news), "negative": 0},
            "key_insights": ["Data retrieved but AI analysis failed"],
            "top_headlines": news[:3],
            "catalysts": [],
            "risks": [],
            "agent": self.NAME,
            "duration_ms": int((time.time() - start) * 1000),
            "tools_called": ["get_news"],
        }


# ─────────────────────────────────────────────────────────────────────────────
# 4. Macro Agent  ← Agentic RAG: calls search_macro_knowledge() FIRST
# ─────────────────────────────────────────────────────────────────────────────

class MacroAgent(BaseAgent):
    """
    Evaluates macroeconomic context using ChromaDB RAG + real stock data.
    Competition Concept #4: Agentic RAG — retrieves macro knowledge BEFORE reasoning.
    """

    NAME = "macro"

    def __init__(self):
        super().__init__()
        self.skill = _load_skill("macro_skill.md")

    async def analyze(self, symbol: str) -> Dict[str, Any]:
        start = time.time()
        logger.info("[MacroAgent] Analyzing %s (RAG-first)", symbol)
        try:
            # ── Step 1: Get sector to build relevant RAG query ──────────────
            price_data = self.mcp.get_stock_price(symbol)
            sector = price_data.get("data", {}).get("sector", "equity")

            # ── Step 2: Agentic RAG — query ChromaDB FIRST ──────────────────
            rag_query = f"India {sector} sector outlook economic trends"
            rag_result = self.mcp.search_macro_knowledge(rag_query, top_k=3)
            rag_context = rag_result.get("data", [])

            # Secondary RAG query for broader macro context
            rag_result2 = self.mcp.search_macro_knowledge("India GDP inflation RBI monetary policy", top_k=2)
            rag_context += rag_result2.get("data", [])

            # If ChromaDB returns nothing (cold start), use inline knowledge base snippets
            if not rag_context:
                logger.warning("[MacroAgent] ChromaDB returned empty — using inline macro fallback")
                rag_context = self._get_inline_macro_context(sector)

            # ── Step 3: Also fetch fundamentals for debt/rate sensitivity ──
            fund_data = self.mcp.get_fundamentals(symbol)

            data_str = json.dumps({
                "symbol": symbol,
                "sector": sector,
                "price_info": price_data.get("data", {}),
                "fundamentals": fund_data.get("data", {}),
                "rag_macro_context": rag_context,  # ChromaDB retrieved knowledge
            }, indent=2)

            result = await self._call_gemini(self.skill, data_str)
            result["agent"] = self.NAME
            result["duration_ms"] = int((time.time() - start) * 1000)
            result["tools_called"] = ["search_macro_knowledge", "get_stock_price", "get_fundamentals"]
            # Ensure rag_context is in the result for frontend display
            if "rag_context" not in result:
                result["rag_context"] = rag_context
            return result

        except Exception as exc:
            logger.error("[MacroAgent] Error: %s", exc)
            return self._fallback(symbol, start, str(exc))

    def _fallback(self, symbol: str, start: float, error: str) -> Dict[str, Any]:
        return {
            "pillar": "macro",
            "score": 5,
            "signal": "neutral",
            "summary": f"Macro data retrieved for {symbol}. LLM analysis unavailable: {error[:100]}",
            "rag_context": [],
            "macro_factors": {},
            "key_insights": ["RAG retrieval attempted but AI analysis failed"],
            "tailwinds": [],
            "headwinds": [],
            "agent": self.NAME,
            "duration_ms": int((time.time() - start) * 1000),
            "tools_called": ["search_macro_knowledge", "get_stock_price", "get_fundamentals"],
        }

    def _get_inline_macro_context(self, sector: str) -> list:
        """Inline fallback macro context when ChromaDB returns empty."""
        base = [
            {"text": "India GDP growth rate is around 6.5-7% for FY2025, driven by domestic consumption and infrastructure spending. RBI maintains a cautious monetary stance.", "relevance": 0.9},
            {"text": "RBI repo rate stands at 6.5%. Inflation is tracked via CPI targeting 4% with a tolerance band of +/-2%. Monetary policy is data-dependent.", "relevance": 0.85},
            {"text": "India current account deficit is manageable at ~1.5% of GDP. Forex reserves above $600 billion provide strong import cover.", "relevance": 0.8},
        ]
        sector_context = {
            "Technology": {"text": "India IT sector benefits from global digital transformation. Rupee depreciation boosts export earnings. US slowdown risk for discretionary spending.", "relevance": 0.9},
            "Banking": {"text": "Indian banking sector shows strong credit growth at 14-16% YoY. NPA ratios have improved. RBI regulations on LCR and NBFC oversight are key.", "relevance": 0.9},
            "Energy": {"text": "India is a net crude oil importer. Oil price volatility directly impacts refining margins and fuel subsidy burden. Renewable energy transition accelerating.", "relevance": 0.9},
            "Consumer": {"text": "Rural demand recovery is key for FMCG. Premiumisation trend in urban India. GST collections robust indicating healthy consumption.", "relevance": 0.85},
            "Pharma": {"text": "India pharma benefits from generic exports to US and EU. USFDA compliance is critical. Domestic formulations growing at 8-10% annually.", "relevance": 0.85},
        }
        context = base[:]
        for key, val in sector_context.items():
            if key.lower() in sector.lower():
                context.append(val)
                break
        return context



# ─────────────────────────────────────────────────────────────────────────────
# 5. Competitive Agent
# ─────────────────────────────────────────────────────────────────────────────

class CompetitiveAgent(BaseAgent):
    """
    Evaluates competitive positioning vs sector peers.
    Tools used: get_peers, get_fundamentals (for target + each peer)
    """

    NAME = "competitive"

    def __init__(self):
        super().__init__()
        self.skill = _load_skill("competitive_skill.md")

    async def analyze(self, symbol: str) -> Dict[str, Any]:
        start = time.time()
        logger.info("[CompetitiveAgent] Analyzing %s", symbol)
        try:
            # Fetch peers
            peers_result = self.mcp.get_peers(symbol)
            peers = peers_result.get("data", [])

            # Fetch target fundamentals
            target_fund = self.mcp.get_fundamentals(symbol)
            target_price = self.mcp.get_stock_price(symbol)

            # Fetch peer fundamentals (up to 3 peers)
            peer_data = []
            for peer_symbol in peers[:3]:
                try:
                    pf = self.mcp.get_fundamentals(peer_symbol)
                    pp = self.mcp.get_stock_price(peer_symbol)
                    peer_data.append({
                        "symbol": peer_symbol,
                        "fundamentals": pf.get("data", {}),
                        "price_info": pp.get("data", {}),
                    })
                except Exception:
                    peer_data.append({"symbol": peer_symbol, "fundamentals": {}, "price_info": {}})

            data_str = json.dumps({
                "symbol": symbol,
                "target_fundamentals": target_fund.get("data", {}),
                "target_price_info": target_price.get("data", {}),
                "peers": peer_data,
            }, indent=2)

            result = await self._call_gemini(self.skill, data_str)
            result["agent"] = self.NAME
            result["duration_ms"] = int((time.time() - start) * 1000)
            result["tools_called"] = ["get_peers", "get_fundamentals", "get_stock_price"]
            return result

        except Exception as exc:
            logger.error("[CompetitiveAgent] Error: %s", exc)
            return self._fallback(symbol, start, str(exc))

    def _fallback(self, symbol: str, start: float, error: str) -> Dict[str, Any]:
        peers = self.mcp.get_peers(symbol).get("data", [])
        return {
            "pillar": "competitive",
            "score": 5,
            "signal": "neutral",
            "summary": f"Competitive data retrieved for {symbol}. LLM analysis unavailable: {error[:100]}",
            "company_position": "unknown",
            "peer_comparison": {},
            "peers": [{"symbol": p} for p in peers],
            "target_metrics": {},
            "key_insights": ["Data retrieved but AI analysis failed"],
            "competitive_advantages": [],
            "competitive_risks": [],
            "agent": self.NAME,
            "duration_ms": int((time.time() - start) * 1000),
            "tools_called": ["get_peers", "get_fundamentals", "get_stock_price"],
        }
