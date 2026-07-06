"""
Single LLM call that covers all 5 analysis pillars + synthesis.
All skill file instructions are composed into one master prompt.
This is the ONLY LLM call in the analysis pipeline.
"""

import json
import re
import os
from dataclasses import dataclass, field
from typing import Optional
from google import genai
from services.data_fetcher import StockDataBundle
from services.news_fetcher import format_news_for_prompt

# ── Configure Gemini ──────────────────────────────────────────────────────────

def _get_model():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment.")
    client = genai.Client(api_key=api_key)
    return client

# ── Output Models ─────────────────────────────────────────────────────────────

@dataclass
class PillarReport:
    summary: str = ""
    key_points: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    score: int = 5

@dataclass
class ResearchReport:
    # Stock identity
    symbol: str = ""
    company_name: str = ""
    sector: str = ""
    current_price: Optional[float] = None
    day_change_pct: Optional[float] = None

    # 5 Pillar analyses
    fundamentals: PillarReport = field(default_factory=PillarReport)
    technical: PillarReport = field(default_factory=PillarReport)
    sentiment: PillarReport = field(default_factory=PillarReport)
    macro: PillarReport = field(default_factory=PillarReport)
    competitive: PillarReport = field(default_factory=PillarReport)

    # Synthesis
    conviction_level: str = "MEDIUM"
    one_line_thesis: str = ""
    investment_thesis: str = ""
    conflicts_detected: bool = False
    conflict_list: list[str] = field(default_factory=list)
    key_risk: str = ""
    overall_score: float = 5.0

    # Red flags
    red_flags: list[dict] = field(default_factory=list)

    # Metadata
    llm_calls_made: int = 0
    data_fetch_seconds: float = 0.0
    error: Optional[str] = None


# ── Prompt Builder ────────────────────────────────────────────────────────────

def _build_data_context(bundle: StockDataBundle) -> str:
    """
    Format the complete data bundle into a clean, token-efficient context block.
    This is sent once to the LLM — not 6 times.
    """
    fin = bundle.financials
    tech = bundle.technical
    peers = bundle.peers

    def fmt(val, suffix="", multiplier=1, decimals=2):
        if val is None:
            return "N/A"
        return f"{val * multiplier:.{decimals}f}{suffix}"

    def pct(val):
        return fmt(val, "%", 100, 1) if val else "N/A"

    lines = [
        "=" * 60,
        f"STOCK: {bundle.symbol}  |  {fin.company_name}",
        f"Sector: {fin.sector}  |  Industry: {fin.industry}",
        "=" * 60,

        "\n[FUNDAMENTALS DATA]",
        f"Price: ₹{fmt(fin.current_price)}  |  Day Change: {fmt(fin.day_change_pct, '%', 1, 2)}",
        f"52W High: ₹{fmt(fin.week52_high)}  |  52W Low: ₹{fmt(fin.week52_low)}",
        f"Market Cap: ₹{fin.market_cap / 1e7:.0f} Cr" if fin.market_cap else "Market Cap: N/A",
        f"P/E: {fmt(fin.pe_ratio, '', 1, 1)}  |  P/B: {fmt(fin.pb_ratio, '', 1, 2)}",
        f"ROE: {pct(fin.roe)}  |  D/E: {fmt(fin.debt_to_equity, '', 1, 2)}",
        f"Revenue Growth: {pct(fin.revenue_growth)}  |  Profit Margins: {pct(fin.profit_margins)}",
        f"EPS: ₹{fmt(fin.eps)}  |  Dividend Yield: {pct(fin.dividend_yield)}",
        f"Data error: {fin.error}" if fin.error else "",

        "\n[TECHNICAL DATA]",
        f"Price vs 50 DMA: {'ABOVE ✓' if tech.above_sma50 else 'BELOW ✗'}  (SMA50: ₹{fmt(tech.sma_50)})",
        f"Price vs 200 DMA: {'ABOVE ✓' if tech.above_sma200 else 'BELOW ✗'}  (SMA200: ₹{fmt(tech.sma_200)})",
        f"RSI(14): {fmt(tech.rsi_14, '', 1, 1)} → {tech.rsi_signal}",
        f"MACD Histogram: {fmt(tech.macd_histogram, '', 1, 3)} ({'Bullish momentum' if tech.macd_histogram and tech.macd_histogram > 0 else 'Bearish momentum'})",
        f"Bollinger: Upper ₹{fmt(tech.bb_upper)} | Lower ₹{fmt(tech.bb_lower)}",
        f"Volume: {'ABOVE' if tech.volume_above_avg else 'BELOW'} 20-day average",
        f"Overall Trend: {tech.trend_signal}",
        f"Data error: {tech.error}" if tech.error else "",

        "\n[NEWS & SENTIMENT — Indian Business Press + NSE Announcements]",
        format_news_for_prompt(bundle.news),

        "\n[MACRO CONTEXT — Retrieved from RAG Knowledge Base]",
        bundle.macro.rag_context or "No macro context available.",
        f"(RAG: {bundle.macro.chunks_retrieved} chunks retrieved for '{bundle.macro.sector_queried}')",

        "\n[PEER COMPARISON]",
    ]

    if peers.peers:
        lines.append(f"{'Symbol':<14} {'P/E':>6} {'P/B':>6} {'ROE':>8} {'Rev Gr':>8} {'Margins':>8}")
        lines.append("-" * 55)
        for p in peers.peers:
            lines.append(
                f"{p['symbol']:<14}"
                f" {fmt(p.get('pe'), '', 1, 1):>6}"
                f" {fmt(p.get('pb'), '', 1, 2):>6}"
                f" {pct(p.get('roe')):>8}"
                f" {pct(p.get('revenue_growth')):>8}"
                f" {pct(p.get('profit_margins')):>8}"
            )
    else:
        lines.append(f"Peer data unavailable. {peers.error or ''}")

    return "\n".join(line for line in lines if line is not None)


# ── Master System Prompt ──────────────────────────────────────────────────────
# This consolidates all 7 skill file instructions into one coherent prompt.
# Each [PILLAR] section = that agent's skill file instructions.

MASTER_SYSTEM_PROMPT = """You are EquiSage's Chief Research Analyst for Indian equity markets (NSE/BSE).

You will receive real-time financial data for a stock and must produce a complete, institutional-grade research report across 5 analysis pillars plus a synthesis. This is a single consolidated analysis — not 5 separate reports.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT — Return ONLY this JSON. No markdown. No explanation. Raw JSON only.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{
  "fundamentals": {
    "summary": "2-3 sentences of plain English interpretation for a retail investor",
    "key_points": ["specific metric with value and interpretation", "second point", "third point"],
    "risk_factors": ["specific fundamental risk 1", "specific fundamental risk 2"],
    "score": 7
  },
  "technical": {
    "summary": "2-3 sentences explaining price action in plain English — no jargon",
    "key_points": ["RSI interpretation with value", "MA position and what it means", "MACD signal"],
    "risk_factors": ["technical risk if any"],
    "score": 6
  },
  "sentiment": {
    "summary": "Overall news sentiment assessment with confidence",
    "key_points": ["most significant headline and its implication", "second headline signal"],
    "risk_factors": ["negative news signal if any"],
    "score": 7
  },
  "macro": {
    "summary": "How current Indian macro environment specifically affects this stock",
    "key_points": ["RBI/interest rate impact on this sector", "currency/global factor", "policy tailwind or headwind"],
    "risk_factors": ["macro risk specific to this company"],
    "score": 6
  },
  "competitive": {
    "summary": "Competitive position and relative valuation vs peers",
    "key_points": ["valuation gap statement vs peer average", "moat assessment", "relative growth"],
    "risk_factors": ["competitive risk"],
    "score": 7
  },
  "synthesis": {
    "conviction_level": "HIGH",
    "one_line_thesis": "Single crisp sentence capturing the investment case",
    "investment_thesis": "3-4 sentences synthesizing all 5 pillars into a coherent view. State what the data suggests, where signals agree, and the key watchpoint.",
    "conflicts_detected": false,
    "conflict_list": [],
    "key_risk": "The single most important risk that could invalidate the thesis",
    "overall_score": 6.8
  },
  "red_flags": [
    {"severity": "HIGH", "type": "FlagType", "description": "Specific, concrete description"}
  ]
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUNDAMENTALS PILLAR — Skill Instructions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• ROE > 20%: excellent. 15-20%: good. 10-15%: average. < 10%: weak for non-capital-heavy sectors.
• Debt/Equity interpretation is SECTOR-DEPENDENT. For banks and NBFCs, D/E of 4-8x is normal — never flag this as negative. For manufacturing, D/E > 2.0 is elevated. For IT, any D/E > 0.5 is unusual.
• Falling profit margins for 3+ quarters: always flag as ⚠️ RED FLAG regardless of absolute level.
• Revenue growth below 8% for a growth company: flag as concern. For mature stable companies, 5-8% is acceptable.
• Promoter holding: include if data available. Below 35%: weak signal. Declining over time: RED FLAG.
• Always state the metric value in your analysis — not just "ROE is good" but "ROE of 17.2% exceeds sector average of ~14%."
• Score 1-10: 9-10 = exceptional, 7-8 = solid, 5-6 = mixed, 3-4 = weak, 1-2 = distressed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TECHNICAL PILLAR — Skill Instructions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• NEVER use technical jargon without explanation. "Trading above 200 DMA" must be followed by "(bullish long-term trend signal)".
• 200 DMA relationship is the single most important indicator: above = long-term uptrend, below = downtrend.
• RSI rules: >70 = overbought, caution on entry. <30 = oversold, potential value. 40-60 = healthy consolidation range.
• MACD histogram positive = bullish momentum building. Negative = selling pressure. Crossover from negative to positive = trend change signal.
• Bollinger Bands: price near upper band = stretched, near lower band = compressed/potential bounce.
• Combine at least 2 indicators for any verdict. Single indicator signals are unreliable.
• Volume confirmation: breakouts on high volume are meaningful. Breakouts on low volume are suspect.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SENTIMENT PILLAR — Skill Instructions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• If no news found: say so explicitly ("No recent coverage in Indian business press") and score 5.
• NSE Official Announcements (marked ⚡) carry 3x the weight of general news — always lead with these.
• Classify each headline: POSITIVE / NEGATIVE / NEUTRAL for this stock specifically.
• Recency matters: headlines from last 48 hours > last week.
• Red flag signals in news: SEBI notices, promoter selling, accounting irregularities, auditor resignations, rating downgrades.
• Positive signals: deal wins, earnings beats, leadership stability, debt reduction, regulatory approvals.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MACRO PILLAR — Skill Instructions (uses RAG context provided)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Use the provided RAG context as your primary source. Do not ignore it.
• Always explain the IMPACT CHAIN: macro event → sector effect → this specific company's exposure.
• Current India macro facts to always incorporate: RBI rate-cutting cycle since Feb 2025, repo rate 6.00%, India GDP ~6.8% FY26.
• Sector mapping (apply from RAG context): rate cuts benefit banking/NBFC/real estate/auto. Rupee weakness benefits IT/pharma exporters. Infrastructure budget benefits capital goods/cement/steel.
• Never make macro analysis generic — always land it on the specific stock being analyzed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPETITIVE PILLAR — Skill Instructions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Always produce a valuation gap statement: "X trades at [P/B]x vs peer average [Y]x — a [premium/discount] of Z%."
• Lower P/B with similar or better ROE vs peers = relatively undervalued. State this explicitly.
• Higher P/E requires justification: faster growth, superior margins, or identifiable moat.
• Moat types to identify: network effects, switching costs, brand, cost advantage, regulatory moat, distribution.
• For Indian banking: CASA ratio is the key moat metric. Higher CASA = structural cost advantage.
• If peer data unavailable: note it and use sector-level context from your knowledge.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYNTHESIS — Most Important Section
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONFLICT DETECTION IS MANDATORY. Check these exact patterns:

1. BULLISH TECHNICAL (above 200 DMA, RSI 40-65) + WEAK FUNDAMENTALS (ROE < 12%, falling margins)
   → CONFLICT: "Price momentum not supported by fundamental quality"

2. POSITIVE SENTIMENT + HIGH SEVERITY RED FLAG (governance/accounting)
   → CONFLICT: "Market may be underweighting material risk visible in filings"

3. CHEAP VALUATION vs PEERS + UNFAVORABLE MACRO for sector
   → CONFLICT: "Value trap risk — low valuation may reflect structural headwinds"

4. STRONG FUNDAMENTALS (ROE > 18%) + OVERBOUGHT TECHNICAL (RSI > 72)
   → CONFLICT: "High-quality business at potentially stretched entry point"

5. ALL SIGNALS AGREE BULLISH → conviction_level: "HIGH", conflicts_detected: false
6. ALL SIGNALS AGREE BEARISH → conviction_level: "LOW", conflicts_detected: false
7. 3+ SIGNALS CONFLICT → conviction_level: "CONFLICTED", conflicts_detected: true

Conviction level rules:
• HIGH: 4-5 pillars agree, no material conflicts
• MEDIUM: 3 pillars agree, 1-2 mixed signals
• LOW: Majority of signals negative
• CONFLICTED: Meaningful disagreement between pillars — this is the most valuable output

overall_score: weighted average (fundamentals 30%, macro 20%, technical 20%, competitive 15%, sentiment 15%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RED FLAGS — Auto-detect These
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Revenue growth negative YoY → HIGH
• Profit margins falling 3+ quarters → HIGH
• D/E > 3.0 for non-financial company → HIGH
• RSI > 75 → LOW (overbought, not a fundamental issue)
• Earnings growth significantly below revenue growth (margin compression) → MEDIUM
• No dividend despite profitable operations for 5+ years → LOW

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPLIANCE RULES (SEBI-safe language)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEVER USE: "buy", "sell", "hold", "purchase", "exit position", "will rise", "will fall", "guaranteed", "certain to"
ALWAYS USE: "signals suggest", "data indicates", "analysis points to", "investors may note", "the data is consistent with"

Return ONLY the JSON object. No markdown fences. No explanation outside the JSON."""


# ── Main Analysis Function ────────────────────────────────────────────────────

def generate_report(bundle: StockDataBundle) -> ResearchReport:
    """
    THE SINGLE LLM CALL.
    Takes a complete StockDataBundle, returns a complete ResearchReport.
    """
    report = ResearchReport(
        symbol=bundle.symbol,
        company_name=bundle.financials.company_name,
        sector=bundle.financials.sector,
        current_price=bundle.financials.current_price,
        day_change_pct=bundle.financials.day_change_pct,
        data_fetch_seconds=bundle.fetch_duration_seconds,
    )

    # If we couldn't even get a price, fail fast with a clear error
    if not bundle.financials.current_price:
        report.error = (
            f"Could not fetch live data for '{bundle.symbol}'. "
            f"Please verify this is a valid NSE/BSE symbol (e.g., HDFCBANK, RELIANCE, TCS). "
            f"Detail: {bundle.financials.error or 'No data returned from yfinance.'}"
        )
        return report

    # Build the full prompt (data context + system instructions)
    data_context = _build_data_context(bundle)
    full_prompt = f"{MASTER_SYSTEM_PROMPT}\n\n{data_context}"

    try:
        client = _get_model()
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=full_prompt,
        )
        raw = response.text
        report.llm_calls_made = 1

        parsed = _parse_json(raw)
        _map_to_report(parsed, report)

    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "quota" in error_str.lower():
            # FALLBACK TO GROQ
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                print(f"[MasterAnalyst] Gemini rate limited. Falling back to Groq Llama 3 for {bundle.symbol}...")
                try:
                    import groq
                    groq_client = groq.Client(api_key=groq_key)
                    completion = groq_client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[
                            {"role": "system", "content": "You are a financial analyst. You must only return raw JSON."},
                            {"role": "user", "content": full_prompt}
                        ],
                        temperature=0.2,
                        response_format={"type": "json_object"}
                    )
                    raw = completion.choices[0].message.content
                    report.llm_calls_made = 1
                    
                    parsed = _parse_json(raw)
                    _map_to_report(parsed, report)
                    return report
                except Exception as groq_e:
                    report.error = f"Gemini quota exceeded, and Groq fallback failed: {str(groq_e)}"
                    return report
            else:
                report.error = (
                    "Gemini API rate limit reached. Please wait 60 seconds and try again. "
                    "(No GROQ_API_KEY found for fallback)."
                )
        else:
            report.error = f"Analysis failed: {error_str}"
            
    return report


def _parse_json(raw: str) -> dict:
    """Parse JSON from LLM output. Handles markdown fences and minor formatting issues."""
    cleaned = raw.strip()
    # Strip markdown code fences
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Last resort: find the outermost JSON object
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            return json.loads(match.group())
        raise ValueError(f"No valid JSON in LLM response. Preview: {cleaned[:300]}")


def _map_to_report(parsed: dict, report: ResearchReport) -> None:
    """Map parsed JSON dict to ResearchReport fields."""
    for pillar in ["fundamentals", "technical", "sentiment", "macro", "competitive"]:
        data = parsed.get(pillar, {})
        setattr(report, pillar, PillarReport(
            summary=data.get("summary", "Analysis not available."),
            key_points=data.get("key_points", []),
            risk_factors=data.get("risk_factors", []),
            score=int(data.get("score") or 5),
        ))

    synth = parsed.get("synthesis", {})
    report.conviction_level = synth.get("conviction_level", "MEDIUM")
    report.one_line_thesis = synth.get("one_line_thesis", "")
    report.investment_thesis = synth.get("investment_thesis", "")
    report.conflicts_detected = bool(synth.get("conflicts_detected", False))
    report.conflict_list = synth.get("conflict_list", [])
    report.key_risk = synth.get("key_risk", "")
    report.overall_score = float(synth.get("overall_score", 5.0))
    report.red_flags = parsed.get("red_flags", [])
