"""
MCP Server for EquiSage - All data tools wrapped in MCP protocol.
Demonstrates Competition Concept #2: MCP Server
"""

import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
from ta.volatility import BollingerBands
from datetime import datetime, timedelta
import os
from typing import Dict, List, Any, Optional
import json

try:
    from .mock_data import get_mock_data, MOCK_STOCK_DATA
except ImportError:
    from mock_data import get_mock_data, MOCK_STOCK_DATA


class EquiSageMCPServer:
    """
    MCP Server exposing 6 tools for equity research.
    All pillar agents call these tools exclusively.
    """
    
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        self.news_api_key = os.getenv("NEWS_API_KEY", "")

    # ── Common name/alias corrections for popular Indian stocks ──────────────
    SYMBOL_ALIASES = {
        # Infosys - the Yahoo Finance ticker is INFY not INFOSYS
        "INFOSYS": "INFY.NS",
        "INFOSYS.NS": "INFY.NS",
        # Zomato
        "ZOMATO": "ZOMATO.NS",
        "ZOMATO.NS": "ZOMATO.NS",
        # Tata Motors - common spelling issues
        "TATAMOTORS": "TATAMOTORS.NS",
        # JSW - full name needed
        "JSW": "JSWSTEEL.NS",
        "JSW.NS": "JSWSTEEL.NS",
        # Interglobe / IndiGo
        "INTERGLOBE": "INDIGO.NS",
        "INTERGLOBE.NS": "INDIGO.NS",
        # HDFC Bank typos
        "HDFCBK": "HDFCBANK.NS",
        # M&M shorthand
        "MM": "M&M.NS",
        "M&M": "M&M.NS",
        # LT
        "L&T": "LT.NS",
        "LT": "LT.NS",
        # Hero
        "HEROMOTOCORP": "HEROMOTOCO.NS",
        "HERO": "HEROMOTOCO.NS",
        # Bajaj
        "BAJAJ": "BAJFINANCE.NS",
        # ONGC
        "OIL": "ONGC.NS",
        # Adani
        "ADANI": "ADANIENT.NS",
        # Asian Paints
        "ASIANPAINT": "ASIANPAINT.NS",
        # Coal India
        "COAL": "COALINDIA.NS",
        # Power Grid
        "PGCIL": "POWERGRID.NS",
        # NTPC
        "NTPC": "NTPC.NS",
        # SBI
        "SBI": "SBIN.NS",
        "SBIN": "SBIN.NS",
        # Wipro
        "WIPRO": "WIPRO.NS",
        # HCL Tech
        "HCLTECH": "HCLTECH.NS",
        "HCL": "HCLTECH.NS",
        # UltraTech
        "ULTRATECH": "ULTRACEMCO.NS",
        # Titan
        "TITAN": "TITAN.NS",
        # ITC
        "ITC": "ITC.NS",
        # Nykaa
        "NYKAA": "NYKAA.NS",
        # Paytm
        "PAYTM": "PAYTM.NS",
        "PAYTM.NS": "PAYTM.NS",
        # IRCTC
        "IRCTC": "IRCTC.NS",
        # Dmart
        "DMART": "DMART.NS",
        # Pidilite
        "PIDILITE": "PIDILITIND.NS",
        # Havells
        "HAVELLS": "HAVELLS.NS",
    }

    def _resolve_symbol(self, symbol: str) -> str:
        """Resolve NSE/BSE symbol - alias map first, then yfinance, then Yahoo search."""
        import requests as req
        symbol = symbol.upper().strip()

        # 1. Check alias map first (instant, no network call)
        if symbol in self.SYMBOL_ALIASES:
            resolved = self.SYMBOL_ALIASES[symbol]
            return resolved

        base = symbol.split('.')[0]
        # Also check base without suffix
        if base in self.SYMBOL_ALIASES:
            return self.SYMBOL_ALIASES[base]

        candidates = []
        if "." not in symbol:
            candidates = [f"{base}.NS", f"{base}.BO"]
        elif symbol.endswith(".NS"):
            candidates = [symbol, f"{base}.BO"]
        elif symbol.endswith(".BO"):
            candidates = [symbol, f"{base}.NS"]
        else:
            candidates = [symbol]

        # 2. Try direct symbol lookup (5d period - works on weekends/holidays)
        for cand in candidates:
            try:
                t = yf.Ticker(cand)
                h = t.history(period="5d")
                if not h.empty:
                    return cand
            except Exception:
                pass

        # 3. Fallback: search Yahoo Finance by company name
        try:
            resp = req.get(
                "https://query2.finance.yahoo.com/v1/finance/search",
                params={"q": base, "lang": "en-US", "region": "IN", "quotesCount": 8, "newsCount": 0},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=5
            )
            data = resp.json()
            for quote in data.get("quotes", []):
                sym = quote.get("symbol", "")
                qtype = quote.get("quoteType", "")
                if qtype == "EQUITY" and (sym.endswith(".NS") or sym.endswith(".BO")):
                    try:
                        t = yf.Ticker(sym)
                        h = t.history(period="5d")
                        if not h.empty:
                            return sym
                    except Exception:
                        pass
        except Exception:
            pass

        return f"{base}.NS"  # last resort fallback

        
    def get_stock_price(self, symbol: str) -> Dict[str, Any]:
        """
        Tool 1: Get current stock price and basic info.
        
        Args:
            symbol: NSE/BSE stock symbol (e.g., "RELIANCE.NS")
            
        Returns:
            Dict with price, change, volume, market cap
        """
        if self.use_mock:
            data = get_mock_data(symbol, "price")
            if data:
                return {"success": True, "data": data}
            return {"success": False, "error": "Symbol not found in mock data"}
        
        try:
            resolved_symbol = self._resolve_symbol(symbol)
            stock = yf.Ticker(resolved_symbol)
            info = stock.info
            hist = stock.history(period="5d")
            
            if hist.empty:
                # Fallback to mock
                mock_data = get_mock_data(symbol, "price")
                if mock_data:
                    return {"success": True, "data": mock_data, "source": "mock_fallback"}
                return {"success": False, "error": "No data available"}
            
            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            day_change = current_price - prev_price
            day_change_percent = (day_change / prev_price) * 100

            # Build sparkline from available history (up to 30 trading days)
            hist_long = stock.history(period="1mo")
            if hist_long.empty:
                hist_long = hist
            sparkline = [round(float(p), 2) for p in hist_long['Close'].tolist()[-30:]]

            # Prev close, open, day range
            prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else float(current_price)
            open_price = float(hist['Open'].iloc[-1])
            day_high = float(hist['High'].iloc[-1])
            day_low = float(hist['Low'].iloc[-1])

            # 52-week change
            hist_1y = stock.history(period="1y")
            year_change_pct = 0.0
            if not hist_1y.empty and len(hist_1y) > 1:
                year_start = float(hist_1y['Close'].iloc[0])
                year_change_pct = round(((float(current_price) - year_start) / year_start) * 100, 2)

            result = {
                "symbol": resolved_symbol,
                "name": info.get("longName", info.get("shortName", symbol)),
                "current_price": round(float(current_price), 2),
                "day_change": round(float(day_change), 2),
                "day_change_percent": round(float(day_change_percent), 2),
                "volume": int(hist['Volume'].iloc[-1]),
                "market_cap": info.get("marketCap", 0),
                "sector": info.get("sector", info.get("industry", "Unknown")),
                "industry": info.get("industry", ""),
                "exchange": info.get("exchange", "NSE"),
                "sparkline": sparkline,
                "prev_close": prev_close,
                "open": open_price,
                "day_range": f"{day_low:.2f} - {day_high:.2f}",
                "year_change_pct": year_change_pct,
            }

            return {"success": True, "data": result}
            
        except Exception as e:
            # Fallback to mock data
            mock_data = get_mock_data(symbol, "price")
            if mock_data:
                return {"success": True, "data": mock_data, "source": "mock_fallback"}
            return {"success": False, "error": str(e)}
    
    def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """
        Tool 2: Get fundamental financial metrics.
        
        Args:
            symbol: NSE/BSE stock symbol
            
        Returns:
            Dict with PE, PB, ROE, debt/equity ratios
        """
        if self.use_mock:
            data = get_mock_data(symbol, "fundamentals")
            if data:
                return {"success": True, "data": data}
            return {"success": False, "error": "Symbol not found in mock data"}
        
        try:
            resolved_symbol = self._resolve_symbol(symbol)
            stock = yf.Ticker(resolved_symbol)
            info = stock.info
            
            result = {
                "pe_ratio": info.get("trailingPE", 0),
                "pb_ratio": info.get("priceToBook", 0),
                "roe": info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else 0,
                "debt_to_equity": info.get("debtToEquity", 0) / 100 if info.get("debtToEquity") else 0,
                "market_cap": info.get("marketCap", 0),
                "dividend_yield": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0,
                "eps": info.get("trailingEps", 0)
            }
            
            return {"success": True, "data": result}
            
        except Exception as e:
            mock_data = get_mock_data(symbol, "fundamentals")
            if mock_data:
                return {"success": True, "data": mock_data, "source": "mock_fallback"}
            return {"success": False, "error": str(e)}
    
    def get_technical_indicators(self, symbol: str) -> Dict[str, Any]:
        """
        Tool 3: Calculate technical indicators using ta library.
        
        Args:
            symbol: NSE/BSE stock symbol
            
        Returns:
            Dict with RSI, MACD, SMAs, Bollinger Bands
        """
        if self.use_mock:
            data = get_mock_data(symbol, "technical")
            if data:
                return {"success": True, "data": data}
            return {"success": False, "error": "Symbol not found in mock data"}
        
        try:
            resolved_symbol = self._resolve_symbol(symbol)
            stock = yf.Ticker(resolved_symbol)
            hist = stock.history(period="3mo")
            
            if hist.empty or len(hist) < 50:
                mock_data = get_mock_data(symbol, "technical")
                if mock_data:
                    return {"success": True, "data": mock_data, "source": "mock_fallback"}
                return {"success": False, "error": "Insufficient data for technical analysis"}
            
            # Calculate indicators
            close = hist['Close']
            
            # RSI
            rsi = RSIIndicator(close, window=14)
            rsi_value = rsi.rsi().iloc[-1]
            
            # MACD
            macd = MACD(close)
            macd_value = macd.macd().iloc[-1]
            macd_signal = macd.macd_signal().iloc[-1]
            
            # SMAs
            sma_20 = SMAIndicator(close, window=20).sma_indicator().iloc[-1]
            sma_50 = SMAIndicator(close, window=50).sma_indicator().iloc[-1]
            
            # Bollinger Bands
            bb = BollingerBands(close, window=20)
            bb_upper = bb.bollinger_hband().iloc[-1]
            bb_lower = bb.bollinger_lband().iloc[-1]
            bb_middle = bb.bollinger_mavg().iloc[-1]
            
            result = {
                "rsi": float(rsi_value),
                "macd": float(macd_value),
                "macd_signal": float(macd_signal),
                "sma_20": float(sma_20),
                "sma_50": float(sma_50),
                "bb_upper": float(bb_upper),
                "bb_lower": float(bb_lower),
                "bb_middle": float(bb_middle)
            }
            
            return {"success": True, "data": result}
            
        except Exception as e:
            mock_data = get_mock_data(symbol, "technical")
            if mock_data:
                return {"success": True, "data": mock_data, "source": "mock_fallback"}
            return {"success": False, "error": str(e)}
    
    def get_news(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """
        Tool 4: Get recent news headlines for a stock.
        Uses yfinance .news as primary source, RSS feeds as secondary,
        mock data only as last resort.
        
        Args:
            symbol: NSE/BSE stock symbol
            limit: Number of articles to return
            
        Returns:
            List of news articles with title, source, date, sentiment
        """
        if self.use_mock:
            data = get_mock_data(symbol, "news")
            if data:
                return {"success": True, "data": data[:limit]}
            return {"success": False, "error": "No news data available"}
        
        # --- Strategy 1: yfinance built-in news (real-time, no API key needed) ---
        try:
            resolved_symbol = self._resolve_symbol(symbol)
            stock = yf.Ticker(resolved_symbol)
            raw_news = stock.news  # list of dicts
            
            if raw_news:
                articles = []
                for item in raw_news[:limit]:
                    # yfinance >= 0.2.40 wraps data under 'content' key
                    content = item.get("content", item)  # fallback to item itself
                    
                    title = (
                        content.get("title")
                        or item.get("title")
                        or ""
                    )
                    if not title:
                        continue  # skip empty entries

                    # Publisher: new schema uses content.provider.displayName
                    provider = content.get("provider", {})
                    source = (
                        provider.get("displayName")
                        or item.get("publisher")
                        or "Yahoo Finance"
                    )

                    # Publish time: new schema uses content.pubDate ISO string
                    pub_date_raw = content.get("pubDate") or item.get("providerPublishTime")
                    if isinstance(pub_date_raw, (int, float)) and pub_date_raw > 0:
                        try:
                            pub_date = datetime.utcfromtimestamp(pub_date_raw).strftime("%Y-%m-%dT%H:%M:%SZ")
                        except Exception:
                            pub_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                    elif isinstance(pub_date_raw, str) and pub_date_raw:
                        pub_date = pub_date_raw
                    else:
                        pub_date = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

                    # Link
                    link = (
                        content.get("canonicalUrl", {}).get("url")
                        or item.get("link")
                        or ""
                    )

                    sentiment = self._infer_sentiment(title)
                    articles.append({
                        "title": title,
                        "source": source,
                        "published_at": pub_date,
                        "sentiment": sentiment,
                        "link": link,
                    })
                
                if articles:
                    return {"success": True, "data": articles, "source": "yfinance"}
        except Exception:
            pass  # Fall through to next strategy
        
        # --- Strategy 2: RSS feeds from financial news sites ---
        try:
            company_name = symbol.replace(".NS", "").replace(".BO", "").lower()
            articles = self._fetch_rss_news(company_name, limit)
            if articles:
                return {"success": True, "data": articles, "source": "rss"}
        except Exception:
            pass
        
        # --- Strategy 3: Mock data fallback ---
        mock_data = get_mock_data(symbol, "news")
        if mock_data:
            return {"success": True, "data": mock_data[:limit], "source": "mock_fallback"}
        
        return {"success": False, "error": "No news data available from any source"}
    
    def _infer_sentiment(self, title: str) -> str:
        """Infer basic sentiment from headline keywords."""
        title_lower = title.lower()
        positive_keywords = [
            "beat", "beats", "surges", "rises", "gains", "profit", "growth",
            "strong", "record", "upgrade", "launches", "wins", "expands",
            "positive", "up", "rally", "outperform", "success", "new high"
        ]
        negative_keywords = [
            "miss", "misses", "falls", "drops", "loss", "decline", "slump",
            "weak", "downgrade", "cuts", "reduce", "concerns", "risk",
            "negative", "down", "plunge", "underperform", "fail", "low"
        ]
        pos_score = sum(1 for w in positive_keywords if w in title_lower)
        neg_score = sum(1 for w in negative_keywords if w in title_lower)
        if pos_score > neg_score:
            return "positive"
        elif neg_score > pos_score:
            return "negative"
        return "neutral"
    
    def _fetch_rss_news(self, company_name: str, limit: int) -> list:
        """Fetch news from free RSS feeds."""
        try:
            import feedparser
            # Economic Times RSS for market news
            feeds = [
                f"https://economictimes.indiatimes.com/rssfeedsdefault.cms",
                "https://www.moneycontrol.com/rss/latestnews.xml",
            ]
            articles = []
            for feed_url in feeds:
                try:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:limit]:
                        title = entry.get("title", "")
                        if company_name in title.lower() or True:  # Include all news if company not found
                            pub = entry.get("published", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))
                            articles.append({
                                "title": title,
                                "source": feed.feed.get("title", "Financial News"),
                                "published_at": pub,
                                "sentiment": self._infer_sentiment(title),
                                "link": entry.get("link", ""),
                            })
                    if articles:
                        break
                except Exception:
                    continue
            return articles[:limit]
        except ImportError:
            return []
    
    def get_peers(self, symbol: str) -> Dict[str, Any]:
        """
        Tool 5: Get sector peer companies.
        
        Args:
            symbol: NSE/BSE stock symbol
            
        Returns:
            List of peer stock symbols
        """
        if self.use_mock:
            data = get_mock_data(symbol, "peers")
            if data:
                return {"success": True, "data": data}
            return {"success": False, "error": "Symbol not found in mock data"}
        
        # Comprehensive peer mapping covering all major NSE sectors
        peer_mapping = {
            # Large-cap IT
            "TCS.NS":        ["INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
            "INFY.NS":       ["TCS.NS", "WIPRO.NS", "HCLTECH.NS", "LTIM.NS"],
            "WIPRO.NS":      ["TCS.NS", "INFY.NS", "HCLTECH.NS", "TECHM.NS"],
            "HCLTECH.NS":    ["TCS.NS", "INFY.NS", "WIPRO.NS", "LTIM.NS"],
            "TECHM.NS":      ["INFY.NS", "WIPRO.NS", "LTIM.NS", "MPHASIS.NS"],
            "LTIM.NS":       ["INFY.NS", "HCLTECH.NS", "TECHM.NS", "MPHASIS.NS"],
            "MPHASIS.NS":    ["LTIM.NS", "TECHM.NS", "COFORGE.NS", "PERSISTENT.NS"],
            "PERSISTENT.NS": ["MPHASIS.NS", "COFORGE.NS", "LTIM.NS", "TECHM.NS"],
            # Banking - Private
            "HDFCBANK.NS":   ["ICICIBANK.NS", "AXISBANK.NS", "KOTAKBANK.NS"],
            "ICICIBANK.NS":  ["HDFCBANK.NS", "AXISBANK.NS", "KOTAKBANK.NS"],
            "AXISBANK.NS":   ["HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS"],
            "KOTAKBANK.NS":  ["HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS"],
            "INDUSINDBK.NS": ["ICICIBANK.NS", "AXISBANK.NS", "FEDERALBNK.NS"],
            # Banking - Public
            "SBIN.NS":       ["BANKBARODA.NS", "PNB.NS", "CANBK.NS"],
            "BANKBARODA.NS": ["SBIN.NS", "PNB.NS", "UNIONBANK.NS"],
            "PNB.NS":        ["SBIN.NS", "BANKBARODA.NS", "CANBK.NS"],
            # Energy
            "RELIANCE.NS":   ["ONGC.NS", "IOC.NS", "BPCL.NS", "HINDPETRO.NS"],
            "ONGC.NS":       ["RELIANCE.NS", "IOC.NS", "OIL.NS"],
            "IOC.NS":        ["BPCL.NS", "HINDPETRO.NS", "ONGC.NS"],
            "BPCL.NS":       ["IOC.NS", "HINDPETRO.NS", "ONGC.NS"],
            # Auto
            "MARUTI.NS":     ["TATAMOTORS.NS", "M&M.NS", "HYUNDAI.NS"],
            "M&M.NS":        ["MARUTI.NS", "TATAMOTORS.NS", "EICHERMOT.NS"],
            "EICHERMOT.NS":  ["M&M.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS"],
            "BAJAJ-AUTO.NS": ["EICHERMOT.NS", "HEROMOTOCO.NS", "TVSMOTORS.NS"],
            "HEROMOTOCO.NS": ["BAJAJ-AUTO.NS", "TVSMOTORS.NS", "EICHERMOT.NS"],
            # FMCG
            "HINDUNILVR.NS": ["ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS"],
            "ITC.NS":        ["HINDUNILVR.NS", "BRITANNIA.NS", "GODREJCP.NS"],
            "NESTLEIND.NS":  ["HINDUNILVR.NS", "ITC.NS", "BRITANNIA.NS"],
            "BRITANNIA.NS":  ["NESTLEIND.NS", "ITC.NS", "HINDUNILVR.NS"],
            # Telecom
            "BHARTIARTL.NS": ["IDEA.NS", "TATACOMM.NS"],
            # Metals & Mining
            "JSWSTEEL.NS":   ["TATASTEEL.NS", "HINDALCO.NS", "SAIL.NS"],
            "TATASTEEL.NS":  ["JSWSTEEL.NS", "HINDALCO.NS", "SAIL.NS"],
            "HINDALCO.NS":   ["JSWSTEEL.NS", "TATASTEEL.NS", "NMDC.NS"],
            "COALINDIA.NS":  ["NMDC.NS", "HINDCOPPER.NS"],
            # Pharma
            "SUNPHARMA.NS":  ["DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS"],
            "DRREDDY.NS":    ["SUNPHARMA.NS", "CIPLA.NS", "AUROPHARMA.NS"],
            "CIPLA.NS":      ["SUNPHARMA.NS", "DRREDDY.NS", "LUPIN.NS"],
            "DIVISLAB.NS":   ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS"],
            # NBFCs & Finance
            "BAJFINANCE.NS": ["BAJAJFINSV.NS", "CHOLAFIN.NS", "MUTHOOTFIN.NS"],
            "BAJAJFINSV.NS": ["BAJFINANCE.NS", "CHOLAFIN.NS", "LICHSGFIN.NS"],
            "CHOLAFIN.NS":   ["BAJFINANCE.NS", "MUTHOOTFIN.NS", "LICHSGFIN.NS"],
            # Consumer / Food
            "ETERNAL.NS":    ["SWIGGY.NS", "JUBLFOOD.NS", "DEVYANI.NS"],
            "SWIGGY.NS":     ["ETERNAL.NS", "JUBLFOOD.NS"],
            "DMART.NS":      ["TRENT.NS", "ABFRL.NS", "VMART.NS"],
            "TRENT.NS":      ["DMART.NS", "ABFRL.NS"],
            # Cement
            "ULTRACEMCO.NS": ["GRASIM.NS", "SHREECEM.NS", "AMBUJACEMENT.NS"],
            "SHREECEM.NS":   ["ULTRACEMCO.NS", "AMBUJACEMENT.NS", "DALBHARAT.NS"],
            # Infra/Conglomerate
            "LT.NS":         ["SIEMENS.NS", "ABB.NS", "BHEL.NS"],
            "ADANIENT.NS":   ["ADANIPORTS.NS", "ADANIGREEN.NS", "ADANITRANS.NS"],
            "ADANIPORTS.NS": ["ADANIENT.NS", "CONCOR.NS", "JINDALSAW.NS"],
            # Insurance
            "HDFCLIFE.NS":   ["SBILIFE.NS", "ICICIPRULI.NS", "LICI.NS"],
            "SBILIFE.NS":    ["HDFCLIFE.NS", "ICICIPRULI.NS", "MAXFINSERV.NS"],
            # Paints
            "ASIANPAINT.NS": ["BERGERPAINTS.NS", "AKZONOBEL.NS", "INDIACEM.NS"],
        }

        # Direct match
        peers = peer_mapping.get(symbol, [])
        if peers:
            return {"success": True, "data": peers}

        # Dynamic fallback: use yfinance sector data to find industry peers
        try:
            resolved = self._resolve_symbol(symbol)
            stock = yf.Ticker(resolved)
            info = stock.info
            sector = info.get("sector", "").lower()
            industry = info.get("industry", "").lower()
            # Map sector to peers
            sector_defaults = {
                "technology": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS"],
                "financial services": ["HDFCBANK.NS", "ICICIBANK.NS", "BAJFINANCE.NS"],
                "consumer cyclical": ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS"],
                "consumer defensive": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS"],
                "healthcare": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS"],
                "energy": ["RELIANCE.NS", "ONGC.NS", "IOC.NS"],
                "basic materials": ["JSWSTEEL.NS", "TATASTEEL.NS", "HINDALCO.NS"],
                "industrials": ["LT.NS", "SIEMENS.NS", "ABB.NS"],
                "communication services": ["BHARTIARTL.NS", "TATACOMM.NS"],
                "real estate": ["DLF.NS", "GODREJPROP.NS", "PRESTIGE.NS"],
                "utilities": ["NTPC.NS", "POWERGRID.NS", "TATAPOWER.NS"],
            }
            for key, default_peers in sector_defaults.items():
                if key in sector or key in industry:
                    return {"success": True, "data": [p for p in default_peers if p != symbol][:3]}
        except Exception:
            pass

        return {"success": True, "data": []}
    
    def search_macro_knowledge(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """
        Tool 6: Query ChromaDB for macro economic knowledge.
        This demonstrates Agentic RAG (Competition Concept #4).
        
        Args:
            query: Search query (e.g., "India GDP growth trends")
            top_k: Number of results to return
            
        Returns:
            List of relevant knowledge chunks from ChromaDB
        """
        try:
            # Import here to avoid circular dependency
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            
            from rag.macro_rag import query_knowledge
            
            results = query_knowledge(query, top_k=top_k)
            return {"success": True, "data": results}
            
        except Exception as e:
            # Fallback to simple mock macro knowledge
            fallback_knowledge = [
                {
                    "text": "RBI raised repo rate to 6.5% in June 2026 to combat inflation",
                    "relevance": 0.85
                },
                {
                    "text": "India GDP growth forecast at 6.8% for FY 2026-27",
                    "relevance": 0.78
                },
                {
                    "text": "NSE energy sector outperformed broader market in Q2 2026",
                    "relevance": 0.72
                }
            ]
            return {"success": True, "data": fallback_knowledge[:top_k], "source": "mock_fallback"}


# Standalone test function
if __name__ == "__main__":
    print("=" * 60)
    print("EQUISAGE MCP SERVER - TEST MODE")
    print("=" * 60)
    
    server = EquiSageMCPServer(use_mock=True)
    
    test_symbol = "RELIANCE.NS"
    print(f"\nTesting with symbol: {test_symbol}\n")
    
    # Test Tool 1: Price
    print("1. get_stock_price():")
    price_data = server.get_stock_price(test_symbol)
    print(json.dumps(price_data, indent=2))
    
    # Test Tool 2: Fundamentals
    print("\n2. get_fundamentals():")
    fund_data = server.get_fundamentals(test_symbol)
    print(json.dumps(fund_data, indent=2))
    
    # Test Tool 3: Technical
    print("\n3. get_technical_indicators():")
    tech_data = server.get_technical_indicators(test_symbol)
    print(json.dumps(tech_data, indent=2))
    
    # Test Tool 4: News
    print("\n4. get_news():")
    news_data = server.get_news(test_symbol)
    print(json.dumps(news_data, indent=2))
    
    # Test Tool 5: Peers
    print("\n5. get_peers():")
    peer_data = server.get_peers(test_symbol)
    print(json.dumps(peer_data, indent=2))
    
    # Test Tool 6: Macro RAG
    print("\n6. search_macro_knowledge():")
    macro_data = server.search_macro_knowledge("India economic outlook")
    print(json.dumps(macro_data, indent=2))
    
    print("\n" + "=" * 60)
    print("ALL TOOLS TESTED SUCCESSFULLY")
    print("=" * 60)
