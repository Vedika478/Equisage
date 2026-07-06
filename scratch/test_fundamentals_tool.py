import os
import asyncio
from dotenv import load_dotenv

dotenv_path = os.path.join(os.getcwd(), ".env")
load_dotenv(dotenv_path)

from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part
from agents.fundamentals_agent import fundamentals_agent

runner = InMemoryRunner(agent=fundamentals_agent, app_name="test_fundamentals")

async def test():
    await runner.session_service.create_session(
        app_name="test_fundamentals",
        user_id="user1",
        session_id="session1",
        state={"symbol": "RELIANCE.NS", "sector": "Energy"}
    )
    events = runner.run(
        user_id="user1",
        session_id="session1",
        new_message=Content(role="user", parts=[Part.from_text(text="Fetch and analyze financials for RELIANCE.NS.")]),
    )
    final_state = {}
    for event in events:
        if hasattr(event, "author"):
            print(f"[{event.author}] event received")
        if hasattr(event, "actions") and event.actions:
            if hasattr(event.actions, "state_delta") and event.actions.state_delta:
                final_state.update(event.actions.state_delta)
    print("Agent output:", final_state.get("fundamentals_report"))

asyncio.run(test())
