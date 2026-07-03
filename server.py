from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
from typing import List, Dict, Any

from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part
from agents.root_agent import root_agent

app = FastAPI(title="EquiSage API")

# Add CORS so React frontend (port 5173) can access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "*"],  # allows all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    symbol: str
    sector: str = "Unknown"
    peers: List[str] = []

@app.post("/analyze")
async def analyze_stock(req: AnalyzeRequest):
    try:
        # We need a new session per request for safety
        session_id = f"session_{req.symbol}_{asyncio.get_event_loop().time()}"
        user_id = "demo_user"
        
        initial_state = {
            "symbol": req.symbol,
            "sector": req.sector,
            "peers": req.peers
        }

        # Initialize the runner
        runner = InMemoryRunner(agent=root_agent)
        
        # We must run it synchronously if run() is synchronous, 
        # or use run_async() if ADK provides it. We will use run() in a thread.
        def _run_pipeline():
            runner.session_service.create_session_sync(
                session_id=session_id, 
                user_id=user_id, 
                app_name="equisage"
            )
            
            events = runner.run(
                user_id=user_id,
                session_id=session_id,
                new_message=Content(role="user", parts=[Part.from_text(text=f"Analyze {req.symbol}")]),
                state_delta=initial_state
            )
            
            final_state = {}
            for event in events:
                if hasattr(event, "actions") and event.actions:
                    if hasattr(event.actions, "state_delta") and event.actions.state_delta:
                        final_state.update(event.actions.state_delta)
                if hasattr(event, "state_delta") and event.state_delta:
                    final_state.update(event.state_delta)
            
            return final_state

        # Run the blocking ADK runner in a separate thread to not block the async event loop
        final_state = await asyncio.to_thread(_run_pipeline)
        
        # Transform the state into the format the frontend expects:
        
        # Use yfinance to get REAL market data for the UI
        import yfinance as yf
        ticker = yf.Ticker(req.symbol)
        
        # Get historical data for sparkline (last 30 days)
        hist = ticker.history(period="1mo")
        sparkline = hist['Close'].tolist() if not hist.empty else []
        
        info = ticker.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or (sparkline[-1] if sparkline else 0)
        prev_close = info.get('previousClose') or current_price
        
        change = current_price - prev_close
        changePct = (change / prev_close * 100) if prev_close else 0
        
        def format_large_number(num):
            if not num: return "N/A"
            if num >= 1e12: return f"{round(num/1e12, 2)}T"
            if num >= 1e9: return f"{round(num/1e9, 2)}B"
            if num >= 1e6: return f"{round(num/1e6, 2)}M"
            return str(num)

        # Safely extract LLM scores (default to 50 if missing)
        fundamentals_score = 50
        technical_score = 50
        sentiment_score = 50
        macro_score = 50
        peers_score = 50
        
        # If the LLM didn't return these, we just use defaults. 
        # Ideally the LLM state updates would contain these metrics.
        # Since the synthesis logic might not have output structured numbers, we will mock them for now.
        
        return {
            "symbol": req.symbol,
            "name": info.get("longName", req.symbol.split('.')[0] + " Corporation"),
            "logo": req.symbol[0],
            "price": round(current_price, 2),
            "change": round(change, 2),
            "changePct": round(changePct, 2),
            "sparkline": sparkline,
            "conviction": final_state.get("conflicts_flagged", "neutral"), # 'high', 'neutral', 'conflict'
            "pillars": {
                "fundamentals": fundamentals_score,
                "technical": technical_score,
                "sentiment": sentiment_score,
                "macro": macro_score,
                "peers": peers_score
            },
            "conflicts": final_state.get("conflicts", []),
            "stats": {
                "prevClose": round(prev_close, 2),
                "open": round(info.get('open', current_price), 2),
                "yearChange": round(info.get('52WeekChange', 0) * 100, 2),
                "dayRange": f"{round(info.get('dayLow', 0), 2)} - {round(info.get('dayHigh', 0), 2)}",
                "volume": format_large_number(info.get('volume')),
                "marketCap": format_large_number(info.get('marketCap')),
                "convictionLevel": "High" if not final_state.get("conflicts") else "Mixed",
                "complianceStatus": "Cleared" if final_state.get("compliance_status") else "Flagged"
            },
            "research": {
                "snapshot": final_state.get("synthesis_report", "No snapshot generated."),
                "conflictsFlagged": final_state.get("conflicts_report", "No conflicts detected."),
                "summary": final_state.get("compliance_report", "No compliance summary.")
            },
            # Also attach raw reports for debugging if needed
            "_raw": {
                "fundamentals": final_state.get("fundamentals_report"),
                "technical": final_state.get("technical_report"),
                "sentiment": final_state.get("sentiment_report"),
                "macro": final_state.get("macro_report"),
                "peers": final_state.get("competitive_report"),
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Serve frontend static files
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
