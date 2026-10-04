# Product Vision: EquiSage

## 1. Product Identity
EquiSage is an **evidence-first AI equity research system**.

It is **NOT**:
- A generic stock chatbot.
- A stock prediction model or price-target generator.
- A black-box sentiment score.
- A collection of LLM agents chatting with each other.

It is a rigorous, institutional-grade research platform where **verified source data and deterministic calculations are the absolute source of truth.** The AI's role is to interpret evidence, not to invent it.

## 2. Core Output: The Investment Dossier
The primary artifact EquiSage produces for a user is a comprehensive **Investment Dossier**. This dossier is not a conversational response, but a structured, modular report containing:

1. **Company Overview**: What the business does and how it makes money.
2. **Business Quality**: Moat, management execution, and structural advantages.
3. **Fundamental Analysis**: Deterministic financial health metrics and trends.
4. **Valuation**: Absolute and relative valuation models.
5. **Technical Setup**: Objective price action and momentum indicators.
6. **Event Intelligence**: Recent material events, filings, and earnings.
7. **Macro/Company Exposure**: How broader economic variables impact this specific company.
8. **Competitive Position**: The company's standing relative to defined peers.
9. **Risks**: Structural, cyclical, and execution risks.
10. **Explicit Scenarios**: 
    - Bull Case
    - Base Case
    - Bear Case
11. **Catalysts**: Upcoming events that could drive repricing.
12. **Thesis Invalidation Conditions**: Specific, measurable conditions under which the core thesis is proven wrong.
13. **What to Monitor**: Key metrics to track going forward.
14. **Evidence and Sources**: A strict bibliography tracing claims to raw data.
15. **Research Confidence**: A confidence score based strictly on the *quality and completeness of the evidence*, not arbitrary LLM certainty.

## 3. Product Principles

### The LLM is Not the Source of Truth
Never silently convert missing or uncertain information into confident prose. The system must gracefully handle and explicitly present missing data.

### Presentation-Layer Personalization
The underlying verified evidence is immutable regardless of who asks for it. Personalization (e.g., explaining concepts to a beginner vs. providing dense metrics to an advanced user) happens at the presentation/research-depth layer. The base facts do not change.

## 4. Future Capabilities
The architecture is designed to eventually support:
- **Investor Profiling**: Tailoring the presentation depth to user personas.
- **Goal-Based Planning**: Contextualizing a stock within a user's specific financial goals.
- **Portfolio Intelligence**: Analyzing how a stock interacts with an existing portfolio.
- **Living Theses**: Research reports that update dynamically as new data arrives.
- **Thesis Change Detection**: Alerting the user when an invalidation condition is met.
- **Historical Point-in-Time Research**: Evaluating what the system *would have* said on a specific date using only data available at that time.
- **Evaluation/Backtesting**: Systematically grading the accuracy of past interpretations against subsequent reality.
