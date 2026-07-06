"""
Research Orchestrator — Root SequentialAgent with ParallelAgent fan-out.

Pipeline:
  Step 1 │ ParallelAgent: Run 5 pillar agents concurrently (staggered 1s apart)
  Step 2 │ SynthesisAgent: Detect conflicts, calculate conviction
  Step 3 │ ComplianceAgent: LoopAgent — remove forbidden language
  Step 4 │ Assemble final research card JSON
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict

# Limit concurrent LLM calls to avoid hammering Groq/Gemini rate limits
_LLM_SEMAPHORE = asyncio.Semaphore(3)

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.pillar_agents import (
    FundamentalsAgent, TechnicalAgent, NewsAgent,
    MacroAgent, CompetitiveAgent,
)
from agents.synthesis_agent import SynthesisAgent
from agents.compliance_agent import ComplianceAgent
from tools.mcp_server import EquiSageMCPServer

logger = logging.getLogger(__name__)


class ResearchOrchestrator:
    """
    Root orchestrator: Sequential pipeline with Parallel pillar fan-out.

    This is Google ADK Concept #1: Multi-Agent System using
    SequentialAgent (root) → ParallelAgent (5 pillars) → Synthesis → Compliance
    """

    def __init__(self):
        # Instantiate all agents once (model creation is cheap)
        self.fundamentals = FundamentalsAgent()
        self.technical = TechnicalAgent()
        self.news = NewsAgent()
        self.macro = MacroAgent()
        self.competitive = CompetitiveAgent()
        self.synthesis = SynthesisAgent()
        self.compliance = ComplianceAgent()
        self.mcp = EquiSageMCPServer(use_mock=False)

    async def run_research(self, symbol: str) -> Dict[str, Any]:
        """
        Run the full research pipeline for a stock symbol.
        Returns a complete research card with all pillar analyses,
        synthesis, compliance check, and agent trace.
        """
        symbol = symbol.upper().strip()
        overall_start = time.time()
        logger.info("[Orchestrator] Starting research for %s", symbol)

        # ── Fetch stock header info upfront ─────────────────────────────────
        price_info = self.mcp.get_stock_price(symbol)
        stock_data = price_info.get("data", {})

        # ── STEP 1: ParallelAgent — run 5 pillar agents concurrently ────────
        # Stagger starts by 3 seconds each — this keeps concurrent LLM calls
        # below 10 RPM even at 3s stagger (agents take 3-8s each on average),
        # which is well within both Groq (30 RPM) and Gemini (15 RPM) limits.
        logger.info("[Orchestrator] Step 1: Running 5 pillar agents (staggered parallel)")
        pillar_start = time.time()

        async def run_with_delay(agent, delay: float):
            await asyncio.sleep(delay)
            return await agent.analyze(symbol)

        pillar_tasks = [
            run_with_delay(self.fundamentals, 0.0),
            run_with_delay(self.technical,    2.0),
            run_with_delay(self.news,         4.0),
            run_with_delay(self.macro,        6.0),
            run_with_delay(self.competitive,  8.0),
        ]

        pillar_names = ["fundamentals", "technical", "news_sentiment", "macro", "competitive"]
        pillar_outputs = await asyncio.gather(*pillar_tasks, return_exceptions=True)

        # Map results to named dict
        pillars: Dict[str, Any] = {}
        for name, output in zip(pillar_names, pillar_outputs):
            if isinstance(output, Exception):
                logger.error("[Orchestrator] Pillar %s failed: %s", name, output)
                pillars[name] = {
                    "pillar": name, "score": 5, "signal": "neutral",
                    "summary": f"Analysis failed: {str(output)[:100]}",
                    "key_insights": [], "agent": name, "duration_ms": 0, "tools_called": [],
                }
            else:
                pillars[name] = output

        logger.info("[Orchestrator] Step 1 complete in %.1fs", time.time() - pillar_start)

        # ── STEP 2: SynthesisAgent ───────────────────────────────────────────
        logger.info("[Orchestrator] Step 2: Running synthesis agent")
        synthesis_result = await self.synthesis.analyze(pillars)

        # ── STEP 3: ComplianceAgent (LoopAgent) ──────────────────────────────
        logger.info("[Orchestrator] Step 3: Running compliance agent")
        compliance_result = await self.compliance.analyze(synthesis_result)

        # ── STEP 4: Assemble final research card ─────────────────────────────
        total_duration_ms = int((time.time() - overall_start) * 1000)

        agent_trace = []
        for name, data in pillars.items():
            if isinstance(data, dict):
                agent_trace.append({
                    "agent": name,
                    "status": "completed",
                    "duration_ms": data.get("duration_ms", 0),
                    "tools_called": data.get("tools_called", []),
                })
        agent_trace.append({
            "agent": "synthesis",
            "status": "completed",
            "duration_ms": synthesis_result.get("duration_ms", 0),
            "tools_called": [],
        })
        agent_trace.append({
            "agent": "compliance",
            "status": "completed",
            "duration_ms": compliance_result.get("duration_ms", 0),
            "tools_called": [],
        })

        research_card = {
            # Use resolved symbol from price data if available
            "symbol": stock_data.get("symbol", symbol),
            "company_name": stock_data.get("name", symbol),
            "sector": stock_data.get("sector", "Unknown"),
            "industry": stock_data.get("industry", ""),
            "current_price": stock_data.get("current_price", 0),
            "day_change": stock_data.get("day_change", 0),
            "day_change_percent": stock_data.get("day_change_percent", 0),
            "volume": stock_data.get("volume", 0),
            "market_cap": stock_data.get("market_cap", 0),
            "exchange": stock_data.get("exchange", "NSE"),
            # Price chart & key stats
            "sparkline": stock_data.get("sparkline", []),
            "prev_close": stock_data.get("prev_close", 0),
            "open": stock_data.get("open", 0),
            "day_range": stock_data.get("day_range", "-"),
            "year_change_pct": stock_data.get("year_change_pct", 0),
            "pillars": pillars,
            "synthesis": synthesis_result,
            "compliance": compliance_result,
            "agent_trace": agent_trace,
            "total_duration_ms": total_duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data_source": "real-time" if price_info.get("source") != "mock_fallback" else "mock_fallback",
            "cached": False,
        }

        logger.info(
            "[Orchestrator] Research complete for %s in %.1fs",
            symbol, total_duration_ms / 1000
        )
        return research_card
