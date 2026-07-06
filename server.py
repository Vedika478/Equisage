from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
import json
import re
from typing import List, Dict, Any

from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part
from agents.root_agent import root_agent

app = FastAPI(title="EquiSage API")

# Add CORS so React frontend can access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allows all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    symbol: str
    sector: str = "Unknown"
    peers: List[str] = []

def extract_json(text: str) -> dict:
    if not text:
        return {}
    # Try to find JSON code block
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    json_str = match.group(1) if match else text
    try:
        return json.loads(json_str.strip())
    except Exception:
        # Fallback: try to find first { and last }
        try:
            start = json_str.find("{")
            end = json_str.rfind("}")
            if start != -1 and end != -1:
                return json.loads(json_str[start:end+1])
        except Exception:
            pass
    return {}

def parse_pillar_score(report_text: str, positive_keywords: list, negative_keywords: list, default_val: int = 50) -> int:
    if not report_text:
        return default_val
    text_lower = report_text.lower()
    
    # Look for "signal" or "overall signal" line
    signal_matches = re.findall(r"(?:signal|rating|recommendation)[:\s\-\*#]+(\w+)", text_lower)
    if signal_matches:
        for match in signal_matches:
            if any(pk in match for pk in positive_keywords):
                return 85
            if any(nk in match for nk in negative_keywords):
                return 20
            if "neutral" in match or "parity" in match:
                return 50
                
    # Fallback to simple keyword count
    pos_count = sum(1 for pk in positive_keywords if pk in text_lower)
    neg_count = sum(1 for nk in negative_keywords if nk in text_lower)
    if pos_count > neg_count:
        return 85
    elif neg_count > pos_count:
        return 20
    return default_val

@app.post("/analyze")
async def analyze_stock(req: AnalyzeRequest):
    try:
        # Determine defaults for sector and peers if not provided
        symbol_upper = req.symbol.upper()
        sector = req.sector
        peers = req.peers

        if sector == "Unknown" or not peers:
            sector_map = {
                "TCS.NS": "Technology",
                "INFY.NS": "Technology",
                "WIPRO.NS": "Technology",
                "HCLTECH.NS": "Technology",
                "RELIANCE.NS": "Energy",
                "ONGC.NS": "Energy",
                "BPCL.NS": "Energy",
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
            if sector == "Unknown":
                sector = sector_map.get(symbol_upper, "Unknown")
            if not peers:
                peers = peers_map.get(symbol_upper, [])

        session_id = f"session_{symbol_upper.replace('.', '_')}_{int(asyncio.get_event_loop().time())}"
        user_id = "demo_user"
        
        initial_state = {
            "symbol": symbol_upper,
            "sector": sector,
            "peers": peers,
            "compliance_feedback": "None. This is the first analysis pass."
        }

        # Initialize the runner
        runner = InMemoryRunner(agent=root_agent, app_name="equisage")
        
        # Async session creation
        await runner.session_service.create_session(
            app_name="equisage",
            user_id=user_id,
            session_id=session_id,
            state=initial_state
        )
        
        # Run the blocking ADK runner in a separate thread
        def _run_pipeline():
            events = runner.run(
                user_id=user_id,
                session_id=session_id,
                new_message=Content(role="user", parts=[Part.from_text(text=f"Analyse {symbol_upper}.")]),
            )
            
            final_state = {}
            for event in events:
                if hasattr(event, "actions") and event.actions:
                    if hasattr(event.actions, "state_delta") and event.actions.state_delta:
                        final_state.update(event.actions.state_delta)
                if hasattr(event, "state_delta") and event.state_delta:
                    final_state.update(event.state_delta)
            return final_state

        final_state = await asyncio.to_thread(_run_pipeline)
        
        # Fetch real-time market data from yfinance for the dashboard
        import yfinance as yf
        ticker = yf.Ticker(symbol_upper)
        
        # Get historical data for sparkline (last 30 days)
        hist = ticker.history(period="1mo")
        sparkline = hist['Close'].tolist() if not hist.empty else [0]
        
        info = ticker.info or {}
        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or (sparkline[-1] if sparkline else 0)
        prev_close = info.get('previousClose') or current_price
        
        change = current_price - prev_close
        changePct = (change / prev_close * 100) if prev_close else 0
        
        def format_large_number(num):
            if not num: return "N/A"
            if num >= 1e12: return f"₹{round(num/1e12, 2)}T"
            if num >= 1e9: return f"₹{round(num/1e9, 2)}B"
            if num >= 1e7: return f"₹{round(num/1e7, 2)} Cr"
            if num >= 1e5: return f"₹{round(num/1e5, 2)} L"
            return str(num)

        # Parse LLM reports for scores
        fundamentals_score = parse_pillar_score(final_state.get("fundamentals_report"), ["positive", "strong"], ["negative", "weak"])
        technical_score = parse_pillar_score(final_state.get("technical_report"), ["bullish", "strong", "uptrend"], ["bearish", "weak", "downtrend"])
        sentiment_score = parse_pillar_score(final_state.get("sentiment_report"), ["positive", "bullish", "optimistic"], ["negative", "bearish", "pessimistic"])
        macro_score = parse_pillar_score(final_state.get("macro_report"), ["supportive", "positive", "tailwind"], ["headwind", "negative"])
        peers_score = parse_pillar_score(final_state.get("competitive_report"), ["leader", "premium", "strong"], ["laggard", "weak"])
        
        # Parse compliance report JSON
        compliance_data = extract_json(final_state.get("compliance_report", ""))
        verdict = compliance_data.get("verdict", "FAIL")
        reason = compliance_data.get("reason", "Compliance review failed to produce a structured verdict.")
        final_card = compliance_data.get("final_card") or final_state.get("research_card") or "No research card generated."

        # Parse conviction and conflicts from final_card
        conviction_match = re.search(r"conviction\s+level[:\s\*#]+(\w+)", final_card.lower())
        conviction_level = "Mixed"
        if conviction_match:
            conviction_level = conviction_match.group(1).capitalize()
            if conviction_level not in ["High", "Moderate", "Mixed"]:
                conviction_level = "Mixed"

        # Determine conviction code for frontend (high, neutral, conflict)
        conviction_code = "neutral"
        if conviction_level == "High":
            conviction_code = "high"
        elif conviction_level == "Mixed":
            conviction_code = "conflict"

        # Parse conflicts
        conflicts_parsed = []
        conflict_blocks = re.split(r"⚠\s*conflict", final_card, flags=re.IGNORECASE)
        for block in conflict_blocks[1:]:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if not lines:
                continue
            title = lines[0].lstrip("0123456789:[] ").strip()
            nature = ""
            implication = ""
            resolution = ""
            for line in lines[1:]:
                if line.lower().startswith("- **nature**") or line.lower().startswith("nature:"):
                    nature = line.split(":", 1)[1].strip()
                elif line.lower().startswith("- **implication**") or line.lower().startswith("implication:"):
                    implication = line.split(":", 1)[1].strip()
                elif line.lower().startswith("- **resolution**") or line.lower().startswith("resolution:"):
                    resolution = line.split(":", 1)[1].strip()
            conflicts_parsed.append({
                "title": title,
                "nature": nature,
                "implication": implication,
                "resolution": resolution
            })

        # Extract conflicts as pairs of strings for radar chart connections in UI
        conflicts_list = []
        for c in conflicts_parsed:
            title = c.get("title", "").lower()
            found_pillars = []
            for p in ["fundamentals", "technical", "sentiment", "macro", "peers"]:
                p_variants = [p]
                if p == "technical":
                    p_variants.extend(["technicals", "chart", "price"])
                elif p == "peers":
                    p_variants.extend(["competitive", "peer", "competitors"])
                elif p == "macro":
                    p_variants.extend(["macroeconomic", "regime"])
                if any(v in title for v in p_variants):
                    found_pillars.append(p.capitalize())
            if len(found_pillars) >= 2:
                conflicts_list.append(found_pillars[:2])

        # Split final_card into structural components
        snapshot = "No snapshot generated."
        conflicts_flagged = "No conflicts detected."
        summary = "No compliance summary."

        snapshot_match = re.search(r"### Company Snapshot\s*(.*?)(?=###|$)", final_card, re.DOTALL | re.IGNORECASE)
        if snapshot_match:
            snapshot = snapshot_match.group(1).strip()
            
        conflicts_match = re.search(r"### Conflicts Flagged\s*(.*?)(?=###|$)", final_card, re.DOTALL | re.IGNORECASE)
        if conflicts_match:
            conflicts_flagged = conflicts_match.group(1).strip()
            
        summary_parts = []
        pillar_summary = re.search(r"### Pillar-by-Pillar Summary\s*(.*?)(?=###|$)", final_card, re.DOTALL | re.IGNORECASE)
        if pillar_summary:
            summary_parts.append(pillar_summary.group(1).strip())
        agreement = re.search(r"### Signal Agreement\s*(.*?)(?=###|$)", final_card, re.DOTALL | re.IGNORECASE)
        if agreement:
            summary_parts.append("**Signal Agreement:**\n" + agreement.group(1).strip())
        conviction_header = re.search(r"### Overall Conviction Level\s*(.*?)(?=###|$)", final_card, re.DOTALL | re.IGNORECASE)
        if conviction_header:
            summary_parts.append("**Overall Conviction Level:**\n" + conviction_header.group(1).strip())
            
        # Append disclaimer
        disclaimer_match = re.search(r"(\*\*DISCLAIMER\*\*.*)", final_card, re.DOTALL | re.IGNORECASE)
        if disclaimer_match:
            summary_parts.append(disclaimer_match.group(1).strip())

        if summary_parts:
            summary = "\n\n".join(summary_parts)
        else:
            summary = final_card

        response_data = {
            "symbol": symbol_upper,
            "name": info.get("longName") or (symbol_upper.split('.')[0] + " Corporation"),
            "logo": symbol_upper[0],
            "price": round(current_price, 2) if current_price else 0.0,
            "change": round(change, 2) if change else 0.0,
            "changePct": round(changePct, 2) if changePct else 0.0,
            "sparkline": sparkline,
            "conviction": conviction_code,
            "pillars": {
                "fundamentals": fundamentals_score,
                "technical": technical_score,
                "sentiment": sentiment_score,
                "macro": macro_score,
                "peers": peers_score
            },
            "conflicts": conflicts_list,
            "stats": {
                "prevClose": round(prev_close, 2) if prev_close else 0.0,
                "open": round(info.get('open', current_price), 2) if info.get('open') or current_price else 0.0,
                "yearChange": round(info.get('52WeekChange', 0) * 100, 2) if info.get('52WeekChange') else 0.0,
                "dayRange": f"{round(info.get('dayLow', current_price), 2)} - {round(info.get('dayHigh', current_price), 2)}" if info.get('dayLow') else "N/A",
                "volume": format_large_number(info.get('volume')),
                "marketCap": format_large_number(info.get('marketCap')),
                "convictionLevel": conviction_level,
                "complianceStatus": "Cleared" if verdict == "PASS" else "Flagged"
            },
            "research": {
                "snapshot": snapshot,
                "conflictsFlagged": conflicts_flagged,
                "summary": summary
            },
            "_raw": {
                "fundamentals": final_state.get("fundamentals_report"),
                "technical": final_state.get("technical_report"),
                "sentiment": final_state.get("sentiment_report"),
                "macro": final_state.get("macro_report"),
                "peers": final_state.get("competitive_report"),
                "compliance_reason": reason
            }
        }
        return response_data
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Serve frontend static files
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
