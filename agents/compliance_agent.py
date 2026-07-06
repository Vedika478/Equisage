"""
Compliance Agent — Regulatory Cleanup.

Scans the synthesis final_report for forbidden phrases (buy/sell/recommend etc.)
and rewrites them using compliant language.
"""

import os
from google.adk.agents import LlmAgent
from agents.llm_config import get_robust_llm

_SKILL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills",
    "compliance_skill.md",
)
with open(_SKILL_PATH, encoding="utf-8") as f:
    _INSTRUCTION = f.read()

_INSTRUCTION += """
Please review the following research card:
{research_card}

IMPORTANT OVERRIDE:
You MUST output a valid JSON object matching the JSON structure requested above, but use "final_card" instead of "final_report" for the cleaned report text. Ensure the "verdict" field is "PASS" or "FAIL".
"""

compliance_agent = LlmAgent(
    name="ComplianceAgent",
    model=get_robust_llm(),
    instruction=_INSTRUCTION,
    output_key="compliance_report",
)
