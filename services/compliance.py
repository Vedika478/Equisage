"""
SEBI-safe compliance check via pure Python string matching.
Zero LLM calls. Deterministic. Cannot rate-limit.

The ComplianceAgent in the ADK architecture calls this function.
It is a valid agent — it has a skill (these rules), a tool (this
function), and a clear output responsibility. It does not need
an LLM call to enforce string replacement rules.
"""

from services.master_analyst import ResearchReport

# ── Compliance Rules ──────────────────────────────────────────────────────────

# Forbidden phrase → safe replacement
REPLACEMENTS = {
    "buy this stock":        "consider this stock for research",
    "sell this stock":       "review position in this stock",
    "buy now":               "the signals at this time",
    "sell now":              "the signals at this time",
    "you should buy":        "data suggests reviewing",
    "you should sell":       "data suggests reviewing",
    "strong buy":            "high conviction signal",
    "will definitely rise":  "signals point to potential upside",
    "will definitely fall":  "signals point to potential downside",
    "will rise":             "has upside potential based on current data",
    "will fall":             "faces downside risk based on current signals",
    "guaranteed returns":    "historical performance data",
    "guaranteed":            "indicated by current data",
    "certain to":            "likely to, based on current signals,",
    "must buy":              "worth researching further",
    "must sell":             "worth reviewing",
    "exit immediately":      "monitor closely",
    "invest now":            "review for potential inclusion in research",
}

DISCLAIMER = (
    "\n\n---\n"
    "⚠️ RESEARCH DISCLAIMER: This report is AI-generated analysis for "
    "informational and educational purposes only. It does not constitute "
    "financial advice or a recommendation to buy, sell, or hold any security. "
    "All investment decisions are solely the responsibility of the user. "
    "Past data does not guarantee future performance. "
    "EquiSage is not a SEBI-registered Research Analyst. "
    "Please consult a qualified financial advisor before making investment decisions."
)


def _clean_text(text: str) -> tuple[str, list[str]]:
    """Apply all replacements. Returns cleaned text and list of violations found."""
    violations = []
    cleaned = text

    for forbidden, replacement in REPLACEMENTS.items():
        if forbidden in cleaned.lower():
            violations.append(forbidden)
            # Case-insensitive replacement preserving original case structure
            import re
            cleaned = re.sub(re.escape(forbidden), replacement, cleaned, flags=re.IGNORECASE)

    return cleaned, violations


def run_compliance(report: ResearchReport) -> ResearchReport:
    """
    Apply compliance rules to all text fields in the report.
    Appends disclaimer. Returns clean report.
    Zero LLM calls.
    """
    violations_found = []

    # Clean all text fields
    report.investment_thesis, v = _clean_text(report.investment_thesis)
    violations_found.extend(v)

    report.one_line_thesis, v = _clean_text(report.one_line_thesis)
    violations_found.extend(v)

    for pillar_name in ["fundamentals", "technical", "sentiment", "macro", "competitive"]:
        pillar = getattr(report, pillar_name)
        pillar.summary, v = _clean_text(pillar.summary)
        violations_found.extend(v)
        pillar.key_points = [_clean_text(p)[0] for p in pillar.key_points]
        pillar.risk_factors = [_clean_text(r)[0] for r in pillar.risk_factors]

    if violations_found:
        print(f"[Compliance] Fixed {len(violations_found)} violation(s): {set(violations_found)}")

    # Append disclaimer to investment thesis
    report.investment_thesis += DISCLAIMER

    return report
