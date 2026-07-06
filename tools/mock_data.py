"""
Mock data fallback for 5 demo stocks when APIs are unavailable.
"""

MOCK_STOCK_DATA = {
    "RELIANCE.NS": {
        "price": {
            "symbol": "RELIANCE.NS",
            "name": "Reliance Industries Ltd",
            "current_price": 2456.75,
            "day_change": 32.50,
            "day_change_percent": 1.34,
            "volume": 8234567,
            "market_cap": 16623450000000,
            "sector": "Energy / Telecom",
            "exchange": "NSE"
        },
        "fundamentals": {
            "pe_ratio": 18.45,
            "pb_ratio": 2.12,
            "roe": 22.3,
            "debt_to_equity": 0.54,
            "market_cap": 16623450000000,
            "dividend_yield": 0.35,
            "eps": 133.2
        },
        "technical": {
            "rsi": 78.3,
            "macd": 45.6,
            "macd_signal": 42.1,
            "sma_20": 2389.45,
            "sma_50": 2345.23,
            "bb_upper": 2501.34,
            "bb_lower": 2298.56,
            "bb_middle": 2399.95
        },
        "news": [
            {
                "title": "Reliance Q4 earnings beat estimates",
                "source": "Economic Times",
                "published_at": "2026-07-01T10:30:00Z",
                "sentiment": "positive"
            },
            {
                "title": "Jio 5G expansion continues across India",
                "source": "Business Standard",
                "published_at": "2026-06-30T14:20:00Z",
                "sentiment": "positive"
            },
            {
                "title": "Oil prices impact refining margins",
                "source": "Mint",
                "published_at": "2026-06-29T09:15:00Z",
                "sentiment": "neutral"
            }
        ],
        "peers": ["ONGC.NS", "IOC.NS", "BPCL.NS"]
    },
    "TCS.NS": {
        "price": {
            "symbol": "TCS.NS",
            "name": "Tata Consultancy Services",
            "current_price": 3654.20,
            "day_change": -15.30,
            "day_change_percent": -0.42,
            "volume": 2145890,
            "market_cap": 13345670000000,
            "sector": "IT Services",
            "exchange": "NSE"
        },
        "fundamentals": {
            "pe_ratio": 28.5,
            "pb_ratio": 12.4,
            "roe": 45.6,
            "debt_to_equity": 0.02,
            "market_cap": 13345670000000,
            "dividend_yield": 1.45,
            "eps": 128.3
        },
        "technical": {
            "rsi": 52.4,
            "macd": 12.3,
            "macd_signal": 11.8,
            "sma_20": 3621.45,
            "sma_50": 3589.78,
            "bb_upper": 3712.45,
            "bb_lower": 3534.67,
            "bb_middle": 3623.56
        },
        "news": [
            {
                "title": "TCS wins major cloud contract from UK government",
                "source": "Reuters",
                "published_at": "2026-07-02T11:00:00Z",
                "sentiment": "positive"
            },
            {
                "title": "IT sector faces margin pressure from wage hikes",
                "source": "Economic Times",
                "published_at": "2026-07-01T08:30:00Z",
                "sentiment": "negative"
            }
        ],
        "peers": ["INFY.NS", "WIPRO.NS", "TECHM.NS"]
    },
    "HDFCBANK.NS": {
        "price": {
            "symbol": "HDFCBANK.NS",
            "name": "HDFC Bank Ltd",
            "current_price": 1678.90,
            "day_change": 8.45,
            "day_change_percent": 0.51,
            "volume": 5678234,
            "market_cap": 12789450000000,
            "sector": "Private Banking",
            "exchange": "NSE"
        },
        "fundamentals": {
            "pe_ratio": 19.8,
            "pb_ratio": 2.8,
            "roe": 16.7,
            "debt_to_equity": 5.4,
            "market_cap": 12789450000000,
            "dividend_yield": 1.2,
            "eps": 84.8
        },
        "technical": {
            "rsi": 48.2,
            "macd": -5.4,
            "macd_signal": -3.2,
            "sma_20": 1665.34,
            "sma_50": 1702.45,
            "bb_upper": 1705.67,
            "bb_lower": 1625.23,
            "bb_middle": 1665.45
        },
        "news": [
            {
                "title": "HDFC Bank reports strong deposit growth",
                "source": "Mint",
                "published_at": "2026-07-02T13:45:00Z",
                "sentiment": "positive"
            },
            {
                "title": "RBI rate hike impacts lending margins",
                "source": "Business Standard",
                "published_at": "2026-06-30T16:00:00Z",
                "sentiment": "negative"
            },
            {
                "title": "Digital banking adoption accelerates",
                "source": "Economic Times",
                "published_at": "2026-06-28T10:20:00Z",
                "sentiment": "positive"
            }
        ],
        "peers": ["ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS"]
    },
    "INFY.NS": {
        "price": {
            "symbol": "INFY.NS",
            "name": "Infosys Ltd",
            "current_price": 1523.45,
            "day_change": 18.75,
            "day_change_percent": 1.25,
            "volume": 3456789,
            "market_cap": 6345670000000,
            "sector": "IT Services",
            "exchange": "NSE"
        },
        "fundamentals": {
            "pe_ratio": 25.3,
            "pb_ratio": 8.9,
            "roe": 31.2,
            "debt_to_equity": 0.01,
            "market_cap": 6345670000000,
            "dividend_yield": 2.1,
            "eps": 60.2
        },
        "technical": {
            "rsi": 65.7,
            "macd": 23.4,
            "macd_signal": 19.8,
            "sma_20": 1489.23,
            "sma_50": 1467.89,
            "bb_upper": 1556.78,
            "bb_lower": 1421.67,
            "bb_middle": 1489.23
        },
        "news": [
            {
                "title": "Infosys launches new AI platform for enterprises",
                "source": "Tech Crunch",
                "published_at": "2026-07-01T15:30:00Z",
                "sentiment": "positive"
            },
            {
                "title": "Client project delays in BFSI sector",
                "source": "Mint",
                "published_at": "2026-06-29T12:00:00Z",
                "sentiment": "neutral"
            }
        ],
        "peers": ["TCS.NS", "WIPRO.NS", "HCLTECH.NS"]
    },
    "CHOLAFIN.NS": {
        "price": {
            "symbol": "CHOLAFIN.NS",
            "name": "Cholamandalam Investment and Finance",
            "current_price": 1245.60,
            "day_change": -12.30,
            "day_change_percent": -0.98,
            "volume": 1234567,
            "market_cap": 1023450000000,
            "sector": "NBFC",
            "exchange": "NSE"
        },
        "fundamentals": {
            "pe_ratio": 22.5,
            "pb_ratio": 3.4,
            "roe": 18.9,
            "debt_to_equity": 4.2,
            "market_cap": 1023450000000,
            "dividend_yield": 0.8,
            "eps": 55.4
        },
        "technical": {
            "rsi": 42.3,
            "macd": -8.7,
            "macd_signal": -6.5,
            "sma_20": 1268.45,
            "sma_50": 1289.67,
            "bb_upper": 1312.45,
            "bb_lower": 1224.56,
            "bb_middle": 1268.51
        },
        "news": [
            {
                "title": "Cholamandalam reports strong AUM growth",
                "source": "Business Standard",
                "published_at": "2026-07-01T09:00:00Z",
                "sentiment": "positive"
            },
            {
                "title": "NBFCs face funding cost pressures",
                "source": "Economic Times",
                "published_at": "2026-06-30T11:30:00Z",
                "sentiment": "negative"
            },
            {
                "title": "Vehicle finance segment shows resilience",
                "source": "Mint",
                "published_at": "2026-06-28T14:15:00Z",
                "sentiment": "positive"
            }
        ],
        "peers": ["BAJFINANCE.NS", "MUTHOOTFIN.NS", "LICHSGFIN.NS"]
    }
}


def get_mock_data(symbol: str, data_type: str):
    """
    Get mock data for a symbol and data type.
    
    Args:
        symbol: Stock symbol (e.g., "RELIANCE.NS")
        data_type: One of "price", "fundamentals", "technical", "news", "peers"
    
    Returns:
        Mock data dict or None if not found
    """
    if symbol not in MOCK_STOCK_DATA:
        return None
    
    stock_data = MOCK_STOCK_DATA[symbol]
    
    if data_type not in stock_data:
        return None
    
    return stock_data[data_type]
