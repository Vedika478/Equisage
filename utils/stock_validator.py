"""
Stock Symbol Validator
======================
Validates if a stock symbol exists and is tradeable.
Supports NSE, BSE, and international markets.
"""

import yfinance as yf
from typing import Optional, Dict, Any
import re


class StockValidator:
    """Validates stock symbols and provides basic info."""
    
    # Common Indian stock exchanges
    INDIAN_EXCHANGES = ['.NS', '.BO']  # NSE and BSE
    
    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        """
        Normalize stock symbol to proper format.
        Examples:
            'reliance' -> 'RELIANCE.NS'
            'RELIANCE' -> 'RELIANCE.NS'
            'TCS.NS' -> 'TCS.NS'
            'HDFCBANK.BO' -> 'HDFCBANK.BO'
        """
        symbol = symbol.strip().upper()
        
        # If already has exchange suffix, return as is
        if any(symbol.endswith(ex) for ex in StockValidator.INDIAN_EXCHANGES):
            return symbol
        
        # Default to NSE for Indian stocks
        return f"{symbol}.NS"
    
    @staticmethod
    def validate(symbol: str) -> Dict[str, Any]:
        """
        Validate if a stock symbol exists and return basic info.
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS', 'TCS', 'AAPL')
        
        Returns:
            Dict with:
                - valid: bool
                - symbol: normalized symbol
                - name: company name
                - sector: sector name
                - exchange: exchange name
                - error: error message if invalid
        """
        # Try normalizing for Indian stocks first
        normalized = StockValidator.normalize_symbol(symbol)
        
        # Try NSE first
        result = StockValidator._try_symbol(normalized)
        if result['valid']:
            return result
        
        # If NSE fails and symbol doesn't have exchange, try BSE
        if not any(symbol.upper().endswith(ex) for ex in StockValidator.INDIAN_EXCHANGES):
            bse_symbol = f"{symbol.strip().upper()}.BO"
            result = StockValidator._try_symbol(bse_symbol)
            if result['valid']:
                return result
        
        # Try original symbol as-is (for international stocks)
        if normalized != symbol.strip().upper():
            result = StockValidator._try_symbol(symbol.strip().upper())
            if result['valid']:
                return result
        
        return {
            'valid': False,
            'symbol': symbol,
            'error': f"Stock symbol '{symbol}' not found. Please check the symbol or try adding .NS (NSE) or .BO (BSE) suffix."
        }
    
    @staticmethod
    def _try_symbol(symbol: str) -> Dict[str, Any]:
        """Try fetching data for a specific symbol."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Check if we got valid data
            if not info or len(info) < 5:
                return {'valid': False, 'symbol': symbol, 'error': 'No data available'}
            
            # Check for common error indicators
            if 'symbol' in info and info['symbol'] is None:
                return {'valid': False, 'symbol': symbol, 'error': 'Invalid symbol'}
            
            # Extract basic info
            company_name = (
                info.get('longName') or 
                info.get('shortName') or 
                symbol.split('.')[0]
            )
            
            sector = info.get('sector', 'Unknown')
            industry = info.get('industry', 'Unknown')
            exchange = info.get('exchange', 'Unknown')
            
            # Verify we have at least a price (strong indicator of valid ticker)
            price = (
                info.get('currentPrice') or 
                info.get('regularMarketPrice') or 
                info.get('previousClose')
            )
            
            if price is None or price == 0:
                # Try fetching history as final check
                hist = ticker.history(period='5d')
                if hist.empty:
                    return {'valid': False, 'symbol': symbol, 'error': 'No trading data available'}
                price = float(hist['Close'].iloc[-1])
            
            return {
                'valid': True,
                'symbol': symbol,
                'name': company_name,
                'sector': sector,
                'industry': industry,
                'exchange': exchange,
                'current_price': round(float(price), 2) if price else None,
            }
            
        except Exception as e:
            return {
                'valid': False,
                'symbol': symbol,
                'error': f'Validation failed: {str(e)}'
            }
    
    @staticmethod
    def search_stocks(query: str, limit: int = 10) -> list[Dict[str, Any]]:
        """
        Search for stocks matching query.
        Note: This is a basic implementation. For production, use a proper stock search API.
        
        Args:
            query: Search query
            limit: Max results
        
        Returns:
            List of matching stocks with basic info
        """
        # Common Indian stocks for quick search
        POPULAR_STOCKS = [
            'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
            'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS',
            'LT.NS', 'AXISBANK.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'WIPRO.NS',
            'SUNPHARMA.NS', 'ULTRACEMCO.NS', 'TITAN.NS', 'NESTLEIND.NS', 'BAJFINANCE.NS',
            'HCLTECH.NS', 'ONGC.NS', 'NTPC.NS', 'POWERGRID.NS', 'M&M.NS',
            'TECHM.NS', 'TATAMOTORS.NS', 'ADANIGREEN.NS', 'ADANIENT.NS', 'COALINDIA.NS',
        ]
        
        query_upper = query.upper().strip()
        results = []
        
        # First, try exact match
        exact_match = StockValidator.validate(query)
        if exact_match['valid']:
            results.append(exact_match)
        
        # Then search popular stocks
        for symbol in POPULAR_STOCKS:
            if len(results) >= limit:
                break
            
            base_symbol = symbol.split('.')[0]
            if query_upper in base_symbol or query_upper in symbol:
                if symbol not in [r['symbol'] for r in results]:
                    stock_info = StockValidator.validate(symbol)
                    if stock_info['valid']:
                        results.append(stock_info)
        
        return results[:limit]


# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python stock_validator.py <symbol>")
        print("Example: python stock_validator.py RELIANCE")
        sys.exit(1)
    
    symbol = sys.argv[1]
    result = StockValidator.validate(symbol)
    
    if result['valid']:
        print(f"✓ Valid stock symbol")
        print(f"  Symbol: {result['symbol']}")
        print(f"  Name: {result['name']}")
        print(f"  Sector: {result['sector']}")
        print(f"  Exchange: {result['exchange']}")
        if result.get('current_price'):
            print(f"  Price: ₹{result['current_price']}")
    else:
        print(f"✗ Invalid stock symbol")
        print(f"  Error: {result['error']}")
