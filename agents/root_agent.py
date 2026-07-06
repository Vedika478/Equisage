"""
EquiSage Root Agent
====================
Orchestrates the full pipeline:

  PillarAnalysis (ParallelAgent)     — 5 specialist agents run concurrently
    ├── FundamentalsAgent
    ├── TechnicalAgent
    ├── SentimentAgent
    ├── MacroAgent
    └── CompetitiveAgent
          ↓
  SynthesisAgent (LlmAgent)          — aggregates reports, flags conflicts
          ↓
  ComplianceAgent (LlmAgent)         — enforces guardrails, appends disclaimer

The root_agent is a SequentialAgent containing the above nodes.
It is the entry point for `adk web` and `adk run`.
"""

import os
import sys
import json

from dotenv import load_dotenv

load_dotenv()

from google.adk.agents import ParallelAgent, SequentialAgent

from agents.fundamentals_agent import fundamentals_agent
from agents.technical_agent import technical_agent
from agents.sentiment_agent import sentiment_agent
from agents.macro_agent import macro_agent
from agents.competitive_agent import competitive_agent
from agents.synthesis_agent import synthesis_agent
from agents.compliance_agent import compliance_agent

pillar_analysis = ParallelAgent(
    name="PillarAnalysis",
    sub_agents=[
        fundamentals_agent,
        technical_agent,
        sentiment_agent,
        macro_agent,
        competitive_agent,
    ],
)

root_agent = SequentialAgent(
    name="EquiSageRoot",
    description=(
        "EquiSage multi-agent equity research system for Indian NSE stocks. "
        "Given a stock symbol (e.g. RELIANCE.NS), runs 5 specialist analysis "
        "agents in parallel, synthesises their findings into a Research Card "
        "that explicitly flags signal conflicts, then validates it through a "
        "compliance guardrail agent."
    ),
    sub_agents=[
        pillar_analysis,
        synthesis_agent,
        compliance_agent,
    ],
)

# ---------------------------------------------------------------------------
# CLI entry point (python agents/root_agent.py RELIANCE.NS)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE.NS"

    # Determine defaults for sector and peers based on symbol
    sector_map = {
        "TCS.NS": "Technology",
        "INFY.NS": "Technology",
        "WIPRO.NS": "Technology",
        "HCLTECH.NS": "Technology",
        "RELIANCE.NS": "Energy",
        "ONGC.NS": "Energy",
        "BPCL.NS": "Energy",
        "HDFC.NS": "Banking",
        "HDFCBANK.NS": "Banking",
        "ICICIBANK.NS": "Banking",
        "AXISBANK.NS": "Banking",
    }
    peers_map = {
        "TCS.NS": ["INFY.NS", "WIPRO.NS"],
        "INFY.NS": ["TCS.NS", "WIPRO.NS"],
        "WIPRO.NS": ["TCS.NS", "INFY.NS"],
        "RELIANCE.NS": ["ONGC.NS", "BPCL.NS"],
        "ONGC.NS": ["RELIANCE.NS", "BPCL.NS"],
        "HDFCBANK.NS": ["ICICIBANK.NS", "AXISBANK.NS"],
        "ICICIBANK.NS": ["HDFCBANK.NS", "AXISBANK.NS"],
    }

    sector = sector_map.get(symbol.upper(), "Unknown")
    peers = peers_map.get(symbol.upper(), [])

    print(f"\n{'='*60}")
    print(f"  EquiSage — Equity Research System")
    print(f"  Symbol: {symbol} | Sector: {sector}")
    print(f"  Peers:  {peers}")
    print(f"{'='*60}\n")

    import uuid
    session_id = f"cli_session_{uuid.uuid4().hex[:8]}"

    from google.adk.runners import InMemoryRunner
    from google.genai.types import Content, Part

    runner = InMemoryRunner(agent=root_agent, app_name="equisage")

    # Create a session with initial state (symbol, sector, peers)
    import asyncio

    async def create_session():
        return await runner.session_service.create_session(
            app_name="equisage",
            user_id="cli_user",
            session_id=session_id,
            state={
                "symbol": symbol,
                "sector": sector,
                "peers": peers,
            },
        )

    asyncio.run(create_session())

    print("Running pipeline... (this may take 60–120 seconds)\n")

    events = runner.run(
        user_id="cli_user",
        session_id=session_id,
        new_message=Content(
            role="user",
            parts=[Part.from_text(text=f"Analyse {symbol}.")],
        ),
    )

    # Collect all events and track state
    final_state: dict = {}
    event_count = 0

    for event in events:
        event_count += 1
        if hasattr(event, "author"):
            print(f"[{event.author}] event received")
        if hasattr(event, "actions") and event.actions:
            if hasattr(event.actions, "state_delta") and event.actions.state_delta:
                final_state.update(event.actions.state_delta)

    print(f"\nProcessed {event_count} events.")

    # Output results
    print("\n" + "=" * 60)
    print("PILLAR REPORTS")
    print("=" * 60)

    for key in ["fundamentals_report", "technical_report", "sentiment_report",
                "macro_report", "competitive_report"]:
        val = final_state.get(key, "")
        status = "[OK] PRODUCED" if val else "[ERROR] MISSING"
        print(f"  {key}: {status}")
        if val:
            print(f"    Preview: {str(val)[:100]}...")

    print("\n" + "=" * 60)
    print("RESEARCH CARD (Synthesis)")
    print("=" * 60)
    research_card = final_state.get("research_card", "")
    if research_card:
        print(research_card[:2000])
        if "Conflicts Flagged" in research_card:
            print("\n[OK] 'Conflicts Flagged' section PRESENT")
        else:
            print("\n[WARNING] 'Conflicts Flagged' section NOT FOUND")
    else:
        print("[ERROR] Research card not produced")

    print("\n" + "=" * 60)
    print("COMPLIANCE REPORT")
    print("=" * 60)
    compliance_report = final_state.get("compliance_report", "")
    if compliance_report:
        print(compliance_report[:2000])
        if "DISCLAIMER" in compliance_report.upper():
            print("\n[OK] Disclaimer PRESENT")
        else:
            print("\n[WARNING] Disclaimer NOT FOUND")
    else:
        print("[ERROR] Compliance report not produced")

    # Save full output to file
    output_path = f"equisage_output_{symbol.replace('.', '_')}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_state, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nFull output saved to: {output_path}")
