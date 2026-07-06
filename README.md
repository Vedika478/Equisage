# EquiSage 🔍📈

**Multi-Agent AI Equity Research System for Indian NSE Stocks**

Built with [Google ADK](https://google.github.io/adk-docs/) (Agent Development Kit), Gemini, and a real MCP (Model Context Protocol) data server backed by yfinance.

---

## Problem

Retail and professional investors analysing Indian equity markets must synthesize fundamentals, technicals, market sentiment, macroeconomic context, and competitive positioning — traditionally requiring 5 different analyses done manually and compared subjectively.

EquiSage automates this with 5 specialist AI agents that run **in parallel**, then a synthesis agent that explicitly **flags where signals conflict** (e.g., bullish technicals + deteriorating fundamentals), and finally a compliance guardrail agent that ensures the output is responsible.

---

## Architecture

```
                    User Input (NSE Symbol)
                           │
                    ┌──────▼──────┐
                    │  EquiSage   │  SequentialAgent
                    │  Root Agent │
                    └──────┬──────┘
                           │
              ┌────────────▼────────────┐
              │     PillarAnalysis      │  ParallelAgent (5 concurrent)
              │  ┌───────────────────┐  │
              │  │ FundamentalsAgent │  │──► get_financials (MCP)
              │  │ TechnicalAgent    │  │──► get_price_history (MCP)
              │  │ SentimentAgent    │  │──► get_recent_news (MCP)
              │  │ MacroAgent        │  │──► get_macro_indicators (MCP)
              │  │ CompetitiveAgent  │  │──► get_peer_comparison (MCP)
              │  └───────────────────┘  │
              └──────────┬──────────────┘
                         │  (5 reports written to session state)
                         │
              ┌───────────▼───────────┐
              │    SynthesisAgent     │  LlmAgent
              │  ─ Reads all 5 rpts  │
              │  ─ Detects conflicts  │──► research_card
              │  ─ Conviction level  │
              └───────────┬───────────┘
                          │
              ┌────────────▼────────────┐
              │    ComplianceAgent      │  LlmAgent
              │  ─ No buy/sell lang    │
              │  ─ No return guarantees│──► compliance_report
              │  ─ Appends disclaimer  │──► audit_log.json
              └─────────────────────────┘

  ┌──────────────────────────────────────────────┐
  │  MCP Server (market_data_server.py)          │
  │  Tools:                                      │
  │    get_price_history   → OHLCV + indicators  │
  │    get_financials      → P/E, margins, debt  │
  │    get_peer_comparison → multi-stock compare │
  │    get_recent_news     → headlines / mock    │
  │    get_macro_indicators→ RBI, CPI, sector    │
  └──────────────────────────────────────────────┘
```

---

## Capstone Concepts Demonstrated

| Concept | Implementation |
|---------|---------------|
| **Multi-Agent System** | `ParallelAgent` (5 concurrent pillar agents) + `SequentialAgent` (pipeline orchestration) |
| **MCP Tool Server** | `FastMCP` server wrapping yfinance; agents connect via `MCPToolset` + stdio |
| **Agent Skills** | Each agent loads a domain-specific `skills/*.md` file as its instruction |
| **Session State Memory** | Each agent writes to a distinct `output_key`; no race conditions on shared state |
| **Compliance Guardrail** | `ComplianceAgent` enforces no buy/sell language, appends disclaimer, logs audit trail |
| **Conflict Detection** | `SynthesisAgent` explicitly compares signals across pillars and flags contradictions |

---

## Project Structure

```
equisage/
├── mcp_servers/
│   └── market_data_server.py      # FastMCP server with 5 yfinance-backed tools
├── agents/
│   ├── mcp_helpers.py             # Shared MCPToolset factory
│   ├── fundamentals_agent.py      # P/E, margins, balance sheet
│   ├── technical_agent.py         # MAs, RSI, MACD, volume
│   ├── sentiment_agent.py         # News headlines, management signals
│   ├── macro_agent.py             # RBI rate, inflation, sector context
│   ├── competitive_agent.py       # Peer comparison and ranking
│   ├── synthesis_agent.py         # Conflict-detecting research card
│   ├── compliance_agent.py        # Guardrail + audit log
│   └── root_agent.py              # Pipeline orchestrator (entry point)
├── skills/
│   ├── fundamentals_skill.md
│   ├── technical_skill.md
│   ├── sentiment_skill.md
│   ├── macro_skill.md
│   └── competitive_skill.md
├── tests/
│   └── test_pipeline.py
├── .env.example
├── requirements.txt
└── README.md
```

---

## Setup & Running

### 1. Prerequisites
```bash
python --version  # Python 3.10+ required
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Keys
```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY (Gemini API key)
```

### 4. Run via ADK Web UI (recommended for demo)
```bash
# From the project root (equisage/ parent directory)
adk web equisage/agents/root_agent.py

# Then open http://localhost:8000 in your browser
# Type: "Analyse RELIANCE.NS and produce the full research card"
```

> **Note**: The ADK web command searches for `root_agent` in the specified file.

### 5. Run via CLI
```bash
python agents/root_agent.py RELIANCE.NS
python agents/root_agent.py TCS.NS
python agents/root_agent.py INFY.NS
```

### 6. Run tests (MCP tool unit tests, no LLM)
```bash
pytest tests/test_pipeline.py -v -k "not integration"
```

### 7. Run full integration test (requires Gemini API key, ~5 min)
```bash
pytest tests/test_pipeline.py -v -m integration --timeout=300
```

---

## Supported Symbols

The system works with any NSE `.NS` symbol. The following have been verified:

| Symbol | Company | Default Sector | Default Peers |
|--------|---------|----------------|---------------|
| `RELIANCE.NS` | Reliance Industries | Energy | ONGC.NS, BPCL.NS |
| `TCS.NS` | Tata Consultancy Services | Technology | INFY.NS, WIPRO.NS |
| `INFY.NS` | Infosys | Technology | TCS.NS, WIPRO.NS |

---

## Sample Output

### Research Card excerpt (Synthesis Agent)
```
### Company Snapshot
Reliance Industries (RELIANCE.NS) is India's largest conglomerate by market
capitalisation, operating across Energy, Retail, and Digital Services...

### Conflicts Flagged
⚠ CONFLICT [1]: Technical: Bullish vs Fundamentals: Neutral
  Nature: Price is above all three moving averages (MA20/50/200), RSI at 62...
  However, EV/EBITDA has expanded to 14x, above the 5-year average...
  Implication: Momentum buyers are bidding up the stock ahead of fundamental...
  Resolution: Weight Fundamentals if investing with a 3-year horizon...

### Overall Conviction Level
Conviction Level: Moderate
Signals suggest the company maintains operational strength...
```

### Compliance Report excerpt
```json
{
  "verdict": "PASS",
  "reason": "No buy/sell/hold language detected. Disclaimer appended.",
  "violations_found": [],
  "final_card": "... DISCLAIMER: This is not investment advice ..."
}
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | **Yes** | Gemini API key (get from https://aistudio.google.com) |
| `NEWS_API_KEY` | No | Optional NewsAPI key (yfinance news used as primary; mock used as fallback if both unavailable) |

---

## Known Limitations & Notes

- **yfinance reliability**: The yfinance library occasionally returns empty data for NSE stocks due to Yahoo Finance API changes. All tools handle this gracefully with clear error messages — the pipeline never crashes on data failures.
- **News data**: yfinance provides limited news. If no news is returned, a clearly-labelled mock is used so the pipeline can still demonstrate the full workflow.
- **LLM API costs**: Each pipeline run makes ~7 Gemini API calls. Use `gemini-2.0-flash` (default) to minimise cost.
- **No ML models**: This system intentionally uses no trained ML models. Technical indicators are computed with deterministic math (pandas/numpy).
