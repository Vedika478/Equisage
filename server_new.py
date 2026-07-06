from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
from typing import List, Dict, Any
import os
import sys
import yfinance as yf

# Add utils to path
sys.path.insert(0, os.path.dirname(__file__))

from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part
from agents.root_agent import root_agent

# Import validator if it exists
try:
    from utils.stock_validator import StockValidator
    HAS_VALIDATOR = True
except ImportError:
    HAS_VALIDATOR = False
    print("Warning: Stock validator not available")

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

class ValidateRequest(BaseModel):
    symbol: str

class SearchRequest(BaseModel):
    query: str
    limit: int = 10

@app.post("/validate")
async def validate_stock(req: ValidateRequest):
    """Validate if a stock symbol exists and return basic info"""
    try:
        if HAS_VALIDATOR:
            result = StockValidator.validate(req.symbol)
            return result
        else:
            # Fallback validation using yfinance directly
            symbol = req.symbol.strip().upper()
            if not any(symbol.endswith(ex) for ex in ['.NS', '.BO']):
                symbol = f"{symbol}.NS"
            
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info or len(info) < 5:
                return {
                    'valid': False,
                    'symbol': req.symbol,
                    'error': 'Stock not found'
                }
            
            price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            if not price:
                hist = ticker.history(period='5d')
                if hist.empty:
                    return {'valid': False, 'symbol': req.symbol, 'error': 'No trading data'}
                price = float(hist['Close'].iloc[-1])
            
            return {
                'valid': True,
                'symbol': symbol,
                'name': info.get('longName', symbol.split('.')[0]),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'exchange': info.get('exchange', 'NSE'),
                'current_price': round(float(price), 2)
            }
    except Exception as e:
        return {
            'valid': False,
            'symbol': req.symbol,
            'error': str(e)
        }

@app.post("/search")
async def search_stocks(req: SearchRequest):
    """Search for stocks matching the query"""
    try:
        if HAS_VALIDATOR:
            results = StockValidator.search_stocks(req.query, req.limit)
            return {"results": results}
        else:
            # Simple fallback - just validate the query as a symbol
            validation = await validate_stock(ValidateRequest(symbol=req.query))
            if validation['valid']:
                return {"results": [validation]}
            return {"results": []}
    except Exception as e:
        return {"results": [], "error": str(e)}

@app.get("/popular-stocks")
async def get_popular_stocks():
    """Get list of popular Indian stocks"""
    popular = [
        {'symbol': 'RELIANCE.NS', 'name': 'Reliance Industries', 'sector': 'Energy'},
        {'symbol': 'TCS.NS', 'name': 'Tata Consultancy Services', 'sector': 'Technology'},
        {'symbol': 'HDFCBANK.NS', 'name': 'HDFC Bank', 'sector': 'Banking'},
        {'symbol': 'INFY.NS', 'name': 'Infosys', 'sector': 'Technology'},
        {'symbol': 'ICICIBANK.NS', 'name': 'ICICI Bank', 'sector': 'Banking'},
        {'symbol': 'HINDUNILVR.NS', 'name': 'Hindustan Unilever', 'sector': 'Consumer'},
        {'symbol': 'ITC.NS', 'name': 'ITC Limited', 'sector': 'Consumer'},
        {'symbol': 'SBIN.NS', 'name': 'State Bank of India', 'sector': 'Banking'},
        {'symbol': 'BHARTIARTL.NS', 'name': 'Bharti Airtel', 'sector': 'Telecom'},
        {'symbol': 'KOTAKBANK.NS', 'name': 'Kotak Mahindra Bank', 'sector': 'Banking'},
        {'symbol': 'LT.NS', 'name': 'Larsen & Toubro', 'sector': 'Infrastructure'},
        {'symbol': 'AXISBANK.NS', 'name': 'Axis Bank', 'sector': 'Banking'},
        {'symbol': 'ASIANPAINT.NS', 'name': 'Asian Paints', 'sector': 'Consumer'},
        {'symbol': 'MARUTI.NS', 'name': 'Maruti Suzuki', 'sector': 'Automobile'},
        {'symbol': 'WIPRO.NS', 'name': 'Wipro', 'sector': 'Technology'},
    ]
    return {"stocks": popular}

def get_sector_and_peers(symbol: str) -> tuple[str, list[str]]:
    """
    Dynamically determine sector and peers using yfinance data.
    Falls back to hardcoded mappings if yfinance fails.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        sector = info.get('sector', 'Unknown')
        industry = info.get('industry', '')
        
        # Map to simplified sectors
        sector_mapping = {
            'Technology': 'Technology',
            'Financial Services': 'Banking',
            'Energy': 'Energy',
            'Consumer Cyclical': 'Consumer',
            'Consumer Defensive': 'Consumer',
            'Healthcare': 'Pharmaceuticals',
            'Communication Services': 'Telecom',
            'Industrials': 'Infrastructure',
        }
        
        mapped_sector = sector_mapping.get(sector, sector)
        
        # Peers by sector (common NSE stocks)
        sector_peers = {
            'Technology': ['TCS.NS', 'INFY.NS', 'WIPRO.NS', 'HCLTECH.NS', 'TECHM.NS'],
            'Banking': ['HDFCBANK.NS', 'ICICIBANK.NS', 'AXISBANK.NS', 'SBIN.NS', 'KOTAKBANK.NS'],
            'Energy': ['RELIANCE.NS', 'ONGC.NS', 'BPCL.NS', 'IOC.NS', 'NTPC.NS'],
            'Consumer': ['HINDUNILVR.NS', 'ITC.NS', 'NESTLEIND.NS', 'ASIANPAINT.NS', 'TITAN.NS'],
            'Pharmaceuticals': ['SUNPHARMA.NS', 'DRREDDY.NS', 'CIPLA.NS', 'DIVISLAB.NS', 'BIOCON.NS'],
            'Telecom': ['BHARTIARTL.NS', 'IDEA.NS'],
            'Infrastructure': ['LT.NS', 'ULTRACEMCO.NS', 'GRASIM.NS'],
        }
        
        peers = sector_peers.get(mapped_sector, [])
        # Remove the symbol itself from peers
        peers = [p for p in peers if p != symbol][:4]  # Max 4 peers
        
        return mapped_sector, peers
        
    except Exception as e:
        print(f"Error determining sector/peers: {e}")
        # Fallback to hardcoded
        fallback_map = {
            "TCS.NS": ("Technology", ["INFY.NS", "WIPRO.NS"]),
            "INFY.NS": ("Technology", ["TCS.NS", "WIPRO.NS"]),
            "RELIANCE.NS": ("Energy", ["ONGC.NS", "BPCL.NS"]),
            "HDFCBANK.NS": ("Banking", ["ICICIBANK.NS", "AXISBANK.NS"]),
        }
        return fallback_map.get(symbol, ("Unknown", []))

@app.post("/analyze")
async def analyze_stock(req: AnalyzeRequest):
    try:
        # First validate the symbol
        if HAS_VALIDATOR:
            validation = StockValidator.validate(req.symbol)
        else:
            validation_req = ValidateRequest(symbol=req.symbol)
            validation = await validate_stock(validation_req)
        
        if not validation.get('valid', False):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid stock symbol: {validation.get('error', 'Unknown error')}"
            )
        
        # Use validated symbol
        validated_symbol = validation['symbol']
        
        # Get sector and peers dynamically if not provided
        if req.sector == "Unknown" or not req.peers:
            detected_sector, detected_peers = get_sector_and_peers(validated_symbol)
            sector = req.sector if req.sector != "Unknown" else detected_sector
            peers = req.peers if req.peers else detected_peers
        else:
            sector = req.sector
            peers = req.peers
        
        # We need a new session per request for safety
        session_id = f"session_{validated_symbol}_{asyncio.get_event_loop().time()}"
        user_id = "demo_user"
        
        initial_state = {
            "symbol": validated_symbol,
            "sector": sector,
            "peers": peers
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
                new_message=Content(role="user", parts=[Part.from_text(text=f"Analyze {validated_symbol}")]),
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
        ticker = yf.Ticker(validated_symbol)
        
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
            "symbol": validated_symbol,
            "name": validation.get('name', info.get("longName", validated_symbol.split('.')[0] + " Corporation")),
            "logo": validated_symbol[0],
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
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "EquiSage API"}

# Serve frontend static files
try:
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
except RuntimeError:
    print("Warning: frontend/dist not found. Frontend not served.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server_new:app", host="127.0.0.1", port=8000, reload=True)
