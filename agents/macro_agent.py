"""
MacroAgent — contextualises the current macro-economic environment
(RBI rates, inflation, GDP growth) for the stock's sector.
"""

import os

from google.adk.agents import LlmAgent
from agents.mcp_helpers import make_mcp_toolset

_SKILL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills",
    "macro_skill.md",
)

with open(_SKILL_PATH, encoding="utf-8") as f:
    _SKILL_INSTRUCTION = f.read()

_INSTRUCTION = _SKILL_INSTRUCTION + """

---
## Current Analysis Target
- **Symbol**: {symbol}
- **Sector**: {sector}

CRITICAL tool-calling rules:
- If you need to call a tool, you MUST call it immediately. Do NOT output any conversational text, preamble, explanation, or thinking before calling the tool. Only call the tool.
- Your report MUST be extremely concise, structured in brief bullet points, and strictly under 150 words total. Do not write conversational filler or long paragraphs.
"""

from agents.llm_config import get_robust_llm

macro_agent = LlmAgent(
    name="MacroAgent",
    model=get_robust_llm(),
    instruction=_INSTRUCTION,
    tools=[make_mcp_toolset(tool_filter=["get_macro_indicators"])],
    output_key="macro_report",
)
