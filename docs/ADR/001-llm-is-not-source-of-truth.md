# ADR-001: The LLM is Not the Source of Truth

**Date:** 2026-10-04
**Status:** Accepted

## Context
EquiSage requires extreme accuracy in its financial reporting. The previous architecture allowed the LLM to process raw strings, occasionally relied on the LLM to calculate weighted scores, and utilized silent fallbacks to mock data when API calls failed. This created a high risk of hallucinations, where the system would confidently present invented financial metrics to the user.

## Decision
EquiSage is an **evidence-first** system. 
1. **The LLM is NEVER the authoritative source of financial truth.**
2. All financial data, technical indicators, and relative valuations must be fetched from authoritative APIs and calculated deterministically by standard code (Python/Pandas) *before* being passed to the LLM.
3. The LLM's sole responsibility is *interpretation* and *synthesis* of the verified evidence.
4. If data is missing, it must be explicitly flagged as `MISSING` and passed to the LLM. The system must never silently fall back to mock data in production.

## Consequences
- **Positive:** Eradicates mathematical hallucinations. Ensures total data provenance. Builds user trust.
- **Negative:** Increased complexity in the data engineering layer. The system must gracefully handle sparse data payloads if APIs fail, requiring robust frontend error state handling.
