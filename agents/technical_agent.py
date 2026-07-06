"""
TechnicalAgent — analyses price action, moving averages, RSI, MACD,
and volume trend using pre-computed indicators from get_price_history.
"""

import os

from google.adk.agents import LlmAgent
from agents.mcp_helpers import make_mcp_toolset

_SKILL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills",
    "technical_skill.md",
)

with open(_SKILL_PATH, encoding="utf-8") as f:
    _SKILL_INSTRUCTION = f.read()

_INSTRUCTION = _SKILL_INSTRUCTION + """

---
## Current Analysis Target
- **Symbol**: {symbol}

CRITICAL tool-calling rules:
- If you need to call a tool, you MUST call it immediately. Do NOT output any conversational text, preamble, explanation, or thinking before calling the tool. Only call the tool.
- Your report MUST be extremely concise, structured in brief bullet points, and strictly under 150 words total. Do not write conversational filler or long paragraphs.
"""

from agents.llm_config import get_robust_llm

technical_agent = LlmAgent(
    name="TechnicalAgent",
    model=get_robust_llm(),
    instruction=_INSTRUCTION,
    tools=[make_mcp_toolset(tool_filter=["get_price_history"])],
    output_key="technical_report",
)
