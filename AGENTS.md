# EquiSage Agents Architecture

## 1. Overview
The current repository structure implies a multi-agent system based on 5 domain-specific "pillar" agents (Fundamentals, Technical, Macro, Sentiment, Competitive). However, the actual runtime execution relies on a single monolithic LLM call.

Going forward, EquiSage abandons the arbitrary "5 pillar agents" model. Instead, the agent architecture is designed around functional roles within an **evidence-first** research process. Deterministic calculations are handled by code, while LLM agents are reserved strictly for reasoning, synthesis, and critique based on verified evidence.

## 2. The Target Agent Roles

The target architecture defines three core AI roles, supported by deterministic research modules.

### A. The Research Director (Planner)
**Role:** Plans the research investigation based on the user's request.
**Responsibilities:**
- Interprets user intent (e.g., "Analyze Reliance's recent earnings impact").
- Determines which deterministic research modules (Data Fetchers) need to be invoked to gather necessary evidence.
- Identifies if open-ended document investigation is required (e.g., reading a specific SEC filing or earnings transcript).
- Dispatches tasks to deterministic systems and the AI Analyst.
**Key Constraint:** Does not conduct the research itself; only plans the execution graph.

### B. The AI Analyst (Interpreter & Synthesizer)
**Role:** Interprets verified evidence and constructs investment theses.
**Responsibilities:**
- Receives strict, deterministic data bundles (Normalized Evidence, Calculated Metrics) from the data layer.
- Interprets what the verified evidence implies (e.g., "A rising CASA ratio alongside falling NIMs suggests...").
- Constructs the various sections of the Investment Dossier (Bull Case, Base Case, Bear Case).
- Explicitly links every material claim to the underlying evidence.
**Key Constraint:** Cannot invent data. Must explicitly flag `MISSING` data rather than hallucinating fallbacks.

### C. The AI Critic/Verifier (Validator)
**Role:** Challenges the thesis and verifies evidence chains.
**Responsibilities:**
- Acts as an adversarial reviewer to the AI Analyst.
- Traces every factual claim in the generated thesis back to the raw source data.
- Flags claims that lack sufficient evidence (`UNVERIFIED`) or contradict the deterministic data (`CONFLICTING`).
- Evaluates the thesis invalidation conditions (are they realistic and measurable?).
**Key Constraint:** Has the power to reject a dossier section and send it back to the Analyst for revision.

## 3. Separation of Concerns

- **Data normalization, financial calculations (P/E, ROE, RSI, MACD), and risk metrics** are **NEVER** performed by Agents. These are strictly the domain of Deterministic Research Modules.
- **Agents** only enter the pipeline *after* the Source → Evidence → Calculation chain is complete.
- Personalization (adjusting tone or complexity for beginner vs. advanced investors) is handled at the presentation/output layer by the Analyst, but the underlying verified evidence remains identical.
