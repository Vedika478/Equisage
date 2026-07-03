import os
import asyncio
from dotenv import load_dotenv

dotenv_path = os.path.join(os.getcwd(), ".env")
load_dotenv(dotenv_path)

from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part
from agents.compliance_agent import compliance_agent

runner = InMemoryRunner(agent=compliance_agent, app_name="test_compliance")

sample_card = """
# EQUISAGE RESEARCH CARD: RELIANCE.NS (Energy)
Reliance is a great company.
"""

async def test():
    await runner.session_service.create_session(
        app_name="test_compliance",
        user_id="user1",
        session_id="session1",
        state={
            "symbol": "RELIANCE.NS",
            "research_card": sample_card
        }
    )
    events = runner.run(
        user_id="user1",
        session_id="session1",
        new_message=Content(role="user", parts=[Part.from_text(text=f"Review the research card: {sample_card}")]),
    )
    final_state = {}
    for event in events:
        if hasattr(event, "author"):
            print(f"[{event.author}] event received")
        if hasattr(event, "actions") and event.actions:
            if hasattr(event.actions, "state_delta") and event.actions.state_delta:
                final_state.update(event.actions.state_delta)
    print("Agent output:", final_state.get("compliance_report"))

asyncio.run(test())
