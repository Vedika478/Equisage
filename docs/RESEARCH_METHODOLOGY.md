# Research Methodology

EquiSage enforces a rigorous distinction between different types of information. It is critical that the architecture, prompts, and final UI clearly differentiate between what is a fact, what is a calculation, and what is an AI interpretation.

## 1. Information Hierarchy

### FACT
**Definition:** What an authoritative source reports. It is incontrovertible in the context of the system (though the source itself could be wrong in reality).
**Example:** "Reliance reported Q3 revenue of ₹2.3 lakh crore."
**Handler:** Pure Data Fetchers.

### CALCULATION
**Definition:** What deterministic code computes based on Facts. It is a mathematical certainty given the inputs.
**Example:** "The 50-day moving average is above the 200-day moving average." or "The P/E ratio is 15% lower than the peer group average."
**Handler:** Deterministic Calculation Engine (Python/Pandas).

### INTERPRETATION
**Definition:** What the Evidence (Facts + Calculations) may imply about the future or the business quality. This is subjective and probabilistic.
**Example:** "The golden cross combined with accelerating revenue growth suggests strong institutional buying pressure."
**Handler:** AI Analyst.

### THESIS
**Definition:** The holistic research conclusion and scenario construction based on all preceding Evidence and Interpretations.
**Example:** "The Base Case assumes margins stabilize, resulting in a 15% upside. This thesis is invalidated if RBI raises rates."
**Handler:** AI Analyst, validated by AI Critic.

## 2. Research Process Enforcement

The system must never present an INTERPRETATION as a FACT.
- **Bad:** "The stock is going up because of strong earnings." (Treats a subjective correlation as a fact).
- **Good:** "Earnings grew by 15% [Fact]. Historically, this growth rate correlates with upward momentum [Calculation]. The data suggests continued strength [Interpretation]."

The AI Critic agent is responsible for scanning the draft Dossier to ensure this strict separation of language is maintained.
