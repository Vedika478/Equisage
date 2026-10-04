# Evidence Model

This document defines the strict state transitions and schemas that govern how data becomes a thesis.

## 1. The Authoritative Chain

`SOURCE → EVIDENCE → VALIDATION → CALCULATION → CLAIM → INTERPRETATION → THESIS`

1. **SOURCE**: External origin (e.g., URL, API endpoint).
2. **EVIDENCE**: The raw fetched value.
3. **VALIDATION**: The state of the evidence against schema rules.
4. **CALCULATION**: Deterministic math applied to the evidence.
5. **CLAIM**: A factual statement proposed by the AI Analyst.
6. **INTERPRETATION**: The AI Analyst's reasoning about the claim.
7. **THESIS**: The final synthesized output.

## 2. Evidence State Enums

Every piece of evidence and every claim must be explicitly tagged with one of the following states:

- `VERIFIED`: Sourced from a Tier 1 authoritative source and passes all schema validations.
- `PARTIALLY_VERIFIED`: Sourced from a lower-tier source or lacks complete supporting context.
- `CONFLICTING`: Two or more sources provide contradictory values for the same metric.
- `STALE`: The data is older than the required freshness threshold.
- `MISSING`: The fetcher failed or the data is unavailable. (No mock data allowed).
- `UNVERIFIED`: An AI-generated claim that the Critic could not trace back to the deterministic evidence payload.

## 3. Object Schemas (Conceptual)

### Evidence Node
```json
{
  "id": "ev_123",
  "metric": "pe_ratio",
  "value": 18.5,
  "source_url": "https://...",
  "fetched_at": "2026-10-04T10:00:00Z",
  "state": "VERIFIED"
}
```

### Claim Node (AI Generated)
```json
{
  "id": "cl_456",
  "statement": "The company trades at a premium valuation.",
  "supporting_evidence_ids": ["ev_123", "ev_124"],
  "state": "VERIFIED" 
}
```

### Missing Data Handling
```json
{
  "id": "ev_999",
  "metric": "q3_revenue",
  "value": null,
  "state": "MISSING",
  "reason": "Source API returned 404"
}
```
The AI must read this and output: "Q3 revenue data is currently unavailable."
