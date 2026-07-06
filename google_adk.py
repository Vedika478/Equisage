"""
Multi-provider LLM client for EquiSage - rate-limit safe.

Providers (priority order):
  1. Google Gemini 2.0 Flash  - best quality
  2. Groq llama-3.3-70b       - fast, 30 RPM free, no daily cap
  3. NVIDIA NIM llama-3.3-70b - fallback

Key protections:
  - Global semaphore: max 2 concurrent LLM calls across ALL agents
  - Per-provider cooldown timestamps (not just flags)
  - Round-robin start so agents spread across providers
"""

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, Optional

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# Max 2 concurrent LLM calls globally - prevents burst rate-limit hits
_LLM_SEMAPHORE = asyncio.Semaphore(2)

# ── Provider setup ─────────────────────────────────────────────────────────

# 1. Google Gemini
try:
    from google import genai
    from google.genai import types as genai_types
    _GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
    _gemini_client = genai.Client(api_key=_GEMINI_KEY) if _GEMINI_KEY else None
    GEMINI_MODEL = "gemini-2.0-flash"
    _GEMINI_CONFIG = genai_types.GenerateContentConfig(temperature=0.3, top_p=0.8, max_output_tokens=2048)
    if _GEMINI_KEY: logger.info("OK Gemini -> %s", GEMINI_MODEL)
    else: logger.warning("GEMINI_API_KEY not set")
except Exception as _e:
    _gemini_client = None; _GEMINI_CONFIG = None
    logger.warning("Gemini unavailable: %s", _e)

# 2. Groq
try:
    from groq import Groq as _Groq
    _GROQ_KEY = os.getenv("GROQ_API_KEY", "")
    _groq_client = _Groq(api_key=_GROQ_KEY, max_retries=0) if _GROQ_KEY else None
    GROQ_MODEL = "llama-3.3-70b-versatile"
    if _GROQ_KEY: logger.info("OK Groq -> %s", GROQ_MODEL)
except Exception as _e:
    _groq_client = None
    logger.warning("Groq unavailable: %s", _e)

# 3. NVIDIA NIM
try:
    from openai import OpenAI as _OpenAI
    _NVIDIA_KEY = os.getenv("NVIDIA_API_KEY", "")
    _nvidia_client = _OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=_NVIDIA_KEY, max_retries=0) if _NVIDIA_KEY else None
    NVIDIA_MODEL = "meta/llama-3.3-70b-instruct"
    if _NVIDIA_KEY: logger.info("OK NVIDIA -> %s", NVIDIA_MODEL)
except Exception as _e:
    _nvidia_client = None
    logger.warning("NVIDIA unavailable: %s", _e)

# ── Helpers ────────────────────────────────────────────────────────────────

def strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    return text.strip()

def parse_json_response(raw: str) -> Any:
    cleaned = strip_json_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try: return json.loads(match.group())
            except json.JSONDecodeError: pass
        raise ValueError(f"Could not parse JSON: {cleaned[:300]}")

def _is_quota_error(exc: Exception) -> bool:
    s = str(exc).lower()
    return any(x in s for x in ["429", "quota", "resource_exhausted", "rate_limit", "rate limit", "too many"])

def _is_timeout_error(exc: Exception) -> bool:
    s = str(exc).lower()
    return any(x in s for x in ["timeout", "timed out", "504", "connect"])

# ── Per-provider cooldown tracking ─────────────────────────────────────────
COOLDOWN_SECONDS = 65  # slightly over 1min so rate limit windows reset

_cooldown_until: dict = {"gemini": 0.0, "groq": 0.0, "nvidia": 0.0}

def _available(name: str) -> bool:
    if name == "gemini": return _gemini_client is not None
    if name == "groq":   return _groq_client is not None
    if name == "nvidia": return _nvidia_client is not None
    return False

def _cooled(name: str) -> bool:
    return time.monotonic() >= _cooldown_until[name]

def _hit_quota(name: str) -> None:
    _cooldown_until[name] = time.monotonic() + COOLDOWN_SECONDS
    logger.warning("QUOTA %s -> cooldown %ds", name, COOLDOWN_SECONDS)

def _hit_timeout(name: str) -> None:
    _cooldown_until[name] = time.monotonic() + 20
    logger.warning("TIMEOUT %s -> cooldown 20s", name)

# ── Individual callers ─────────────────────────────────────────────────────

async def _call_gemini(prompt: str) -> str:
    if not _gemini_client: raise RuntimeError("Gemini not configured")
    resp = await asyncio.to_thread(_gemini_client.models.generate_content, model=GEMINI_MODEL, contents=prompt, config=_GEMINI_CONFIG)
    return resp.text

async def _call_groq(prompt: str) -> str:
    if not _groq_client: raise RuntimeError("Groq not configured")
    comp = await asyncio.to_thread(_groq_client.chat.completions.create, model=GROQ_MODEL, messages=[{"role":"user","content":prompt}], temperature=0.3, max_tokens=2048)
    return comp.choices[0].message.content

async def _call_nvidia(prompt: str) -> str:
    if not _nvidia_client: raise RuntimeError("NVIDIA not configured")
    comp = await asyncio.to_thread(_nvidia_client.chat.completions.create, model=NVIDIA_MODEL, messages=[{"role":"user","content":prompt}], temperature=0.3, max_tokens=2048, stream=False, timeout=55)
    return comp.choices[0].message.content

_PROVIDERS = [("gemini", _call_gemini), ("groq", _call_groq), ("nvidia", _call_nvidia)]

# ── Round-robin counter ────────────────────────────────────────────────────
_rr_counter = 0

async def generate_with_retry(prompt: str, max_overall_retries: int = 1) -> str:
    """
    Call LLMs with semaphore + round-robin + cooldown protection.
    - Semaphore prevents >2 concurrent calls
    - Round-robin ensures agents spread across providers
    - Cooldown timestamps replace the simple boolean flags
    """
    async with _LLM_SEMAPHORE:
        global _rr_counter
        start_idx = _rr_counter % len(_PROVIDERS)
        _rr_counter += 1

        n = len(_PROVIDERS)
        last_error: Optional[Exception] = None

        for attempt in range(max_overall_retries + 1):
            tried_any = False

            for i in range(n):
                name, caller = _PROVIDERS[(start_idx + i) % n]
                if not _available(name): continue
                if not _cooled(name):
                    left = _cooldown_until[name] - time.monotonic()
                    logger.debug("  %s cooling (%.0fs left)", name, left)
                    continue

                tried_any = True
                try:
                    result = await caller(prompt)
                    logger.info("LLM OK provider=%s attempt=%d", name, attempt)
                    return result
                except Exception as exc:
                    last_error = exc
                    if _is_quota_error(exc):
                        _hit_quota(name); continue
                    elif _is_timeout_error(exc):
                        _hit_timeout(name); continue
                    else:
                        logger.warning("%s error: %s", name, str(exc)[:100]); continue

            if not tried_any:
                available_names = [n for n, _ in _PROVIDERS if _available(n)]
                if available_names and attempt < max_overall_retries:
                    wait = min((_cooldown_until[n] - time.monotonic() for n in available_names), default=30) + 1
                    wait = max(1, min(wait, 60))
                    logger.warning("All providers cooling. Waiting %.0fs...", wait)
                    await asyncio.sleep(wait)
                else:
                    break
            elif attempt < max_overall_retries:
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError(f"All LLM providers failed after {max_overall_retries+1} attempts. Last: {last_error}") from last_error
