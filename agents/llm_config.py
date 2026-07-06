import os
from google.adk.models.lite_llm import LiteLlm

def get_robust_llm():
    # Use Gemini as primary, fall back to Groq and Nvidia if rate limited or errors occur.
    return LiteLlm(
        model="gemini/gemini-2.0-flash",
        fallbacks=[
            "groq/llama-3.3-70b-versatile", 
            "nvidia/meta/llama-3.1-70b-instruct"
        ],
        num_retries=3
    )
