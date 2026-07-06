"""
Synthesis Agent — The Money Shot for EquiSage.

Receives all 5 pillar analysis outputs, detects signal conflicts,
calculates conviction level, and generates the final research report.
"""

import os
from google.adk.agents import LlmAgent
from agents.llm_config import get_robust_llm

_SKILL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills",
    "synthesis_skill.md",
)
with open(_SKILL_PATH, encoding="utf-8") as f:
    _INSTRUCTION = f.read()

_INSTRUCTION += """
IMPORTANT OVERRIDE:
Ignore the JSON output format requested above.
Instead, you MUST output a pure Markdown report exactly matching this structure, based on the following input data:

### Company Snapshot
[2-3 sentences summarising the business]

### Conflicts Flagged
[List any conflicts, e.g., ⚠ CONFLICT [1]: Technical: Bullish vs Fundamentals: Neutral...]
(If no conflicts, write "No conflicts detected.")

### Overall Conviction Level
Conviction Level: [High/Moderate/Mixed]
[Brief explanation of the conviction level]

### Pillar-by-Pillar Summary
[Brief summary of each pillar's findings]

### Signal Agreement
[Summary of how well the signals align]

Input data from previous agents:
Fundamentals: {fundamentals_report}
Technical: {technical_report}
Sentiment: {sentiment_report}
Macro: {macro_report}
Competitive: {competitive_report}
"""

synthesis_agent = LlmAgent(
    name="SynthesisAgent",
    model=get_robust_llm(),
    instruction=_INSTRUCTION,
    output_key="research_card",
)
