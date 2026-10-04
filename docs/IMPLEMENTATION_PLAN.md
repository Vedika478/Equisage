# Implementation Plan: Migration to Target Architecture

This document outlines the staged migration from the current legacy/monolithic codebase to the target Hybrid Modular Monolith architecture.

## Phase 1: The Purge (Cleanup)
**Goal:** Remove dead code, confusing abstractions, and theatrical AI implementations.
1. **Delete Broken Agents:** Remove `agents/orchestrator.py` and `agents/pillar_agents.py`.
2. **Eradicate Mock Data:** Delete `tools/mock_data.py`. Strip all mock fallback logic from `tools/mcp_server.py` and `services/data_fetcher.py`. If data fails, the system must fail gracefully.
3. **Consolidate MCP Servers:** Standardize entirely on `mcp_servers/market_data_server.py` (FastMCP) and remove `tools/mcp_server.py`.
4. **Remove Fake RAG:** Delete the hardcoded static text in `rag/knowledge_base.json` and associated seeding logic.

## Phase 2: Establish the Deterministic Core
**Goal:** Build the strict Data Architecture and Evidence Model.
1. **Define Schemas:** Implement Pydantic models for the schemas defined in `EVIDENCE_MODEL.md`.
2. **Refactor Fetchers:** Update `services/data_fetcher.py` and `services/news_fetcher.py` to return data strictly adhering to the new Evidence schemas, including `source_url`, `timestamp`, and `state` (`VERIFIED`, `MISSING`, etc.).
3. **Isolate Calculations:** Move all math (moving averages, peer ranking) out of fetchers and into a dedicated `CalculationEngine` module.

## Phase 3: Implement the AI Roles
**Goal:** Replace the monolithic LLM call with the Research Director, AI Analyst, and AI Critic.
1. **Dismantle Master Analyst:** Break down `services/master_analyst.py`.
2. **Create AI Analyst:** Implement the AI Analyst prompt focusing entirely on interpretation and strict citation of the new Evidence payload.
3. **Create AI Critic:** Implement the verification step to scan the Analyst's output for hallucinations or unverified claims.
4. **Create Research Director:** Implement the orchestrator that decides which data fetchers to run and coordinates the Analyst and Critic.

## Phase 4: Integration and Evaluation
**Goal:** Connect the new backend to the frontend and validate accuracy.
1. **Update API Entrypoint:** Modify `main.py` to call the new Research Director instead of the legacy `pipeline.py`.
2. **Run Golden Tests:** Execute the Evaluation framework against the Golden Dataset to ensure zero hallucinations and correct handling of `MISSING` data.
3. **Frontend Adjustments:** Update the React frontend to display the new Investment Dossier format, specifically highlighting the explicit Evidence citations and Confidence scores.
