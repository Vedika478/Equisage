"""
FundamentalsAgent — analyses P/E, margins, balance sheet health
using the get_financials MCP tool.
"""

import os

from google.adk.agents import LlmAgent
from agents.mcp_helpers import make_mcp_toolset

# Load skill instruction from file (path relative to project root)
_SKILL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills",
    "fundamentals_skill.md",
)

with open(_SKILL_PATH, encoding="utf-8") as f:
    _SKILL_INSTRUCTION = f.read()

# Append state-injection prompt so the agent knows which symbol to analyse
_INSTRUCTION = _SKILL_INSTRUCTION + """

---
## Current Analysis Target
- **Symbol**: {symbol}
- **Sector**: {sector}

CRITICAL tool-calling rules:
- If you need to call a tool, you MUST call it immediately. Do NOT output any conversational text, preamble, explanation, or thinking before calling the tool. Only call the tool.
- Your report MUST be extremely concise, structured in brief bullet points, and strictly under 150 words total. Do not write conversational filler or long paragraphs.
"""

from google.adk.models.lite_llm import LiteLlm

fundamentals_agent = LlmAgent(
    name="FundamentalsAgent",
    model=LiteLlm(model="groq/llama-3.3-70b-versatile", num_retries=5),
    instruction=_INSTRUCTION,
    tools=[make_mcp_toolset(tool_filter=["get_financials"])],
    output_key="fundamentals_report",
)
