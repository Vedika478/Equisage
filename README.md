# EquiSage 🔍📈

**Multi-Agent AI Equity Research System for Indian NSE Stocks**

Built with Gemini/Groq, and a Model Context Protocol (MCP) data server backed by yfinance.

---

## 🏆 Project Overview

Retail and professional investors analysing Indian equity markets must synthesize fundamentals, technicals, market sentiment, macroeconomic context, and competitive positioning — traditionally requiring 5 different analyses done manually and compared subjectively.

EquiSage automates this with **5 specialist AI agents** that run **in parallel**, a synthesis agent that explicitly **flags where signals conflict** (e.g., bullish technicals + deteriorating fundamentals), and finally a compliance guardrail agent that ensures the output is responsible.

---

## 🚀 Live Demo & Deployment

This project is fully Dockerized and ready to be deployed on **Hugging Face Spaces**.

### How to deploy to Hugging Face Spaces (For Judges/Evaluators)
1. Log in to [Hugging Face](https://huggingface.co/) and click **Create new Space**.
2. Set the Space name to `EquiSage`.
3. Choose **Docker** as the Space SDK and select **Blank**.
4. Under **Settings -> Variables and secrets**, add your API keys:
   - `GEMINI_API_KEY` (or `GROQ_API_KEY` depending on your LLM config)
5. Push this GitHub repository to the Space (or connect it directly).
6. Hugging Face will automatically detect the `Dockerfile`, build the frontend and backend, and serve the application live!

*(Note: The static GitHub Pages link only hosts the frontend UI and will not function without the backend API attached).*

---

## 🏗️ Architecture

EquiSage uses a cutting-edge pipeline:
- **Pillar Analysis (Parallel Agents)**: 5 Agents (Fundamentals, Technical, Sentiment, Macro, Competitive) run concurrently, pulling real-time data via MCP Tools.
- **Synthesis Agent**: Reads all 5 reports, detects conflicts, and generates a cohesive research card.
- **Compliance Agent**: Enforces guardrails (no buy/sell guarantees) and logs audit trails.
- **FastAPI + React Dashboard**: A premium, responsive UI featuring real-time charts and signal mapping.

---

## 💻 Local Development

### 1. Prerequisites
- Python 3.10+
- Node.js 20+

### 2. Backend Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Configure Environment Variables
cp .env.example .env
# Add your GEMINI_API_KEY to the .env file

# Run the FastAPI Server
python main.py
```
*The backend server will start on `http://localhost:8000`.*

### 3. Frontend Setup
```bash
# Open a new terminal and navigate to the frontend folder
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```
*The frontend will start on `http://localhost:5173`.*

---

## 📦 Project Structure

```text
equisage/
├── Dockerfile                     # Multi-stage Docker build for HF Spaces
├── main.py                        # FastAPI Server Entry Point
├── agents/                        # AI Agent Definitions
├── frontend/                      # React/Vite Frontend Application
│   ├── src/                       # UI Components & Styling
│   └── package.json               # Node dependencies
├── mcp_servers/                   # FastMCP Data servers
├── rag/                           # ChromaDB knowledge base logic
├── services/                      # Pipeline orchestrator
├── skills/                        # Agent instructions (.md)
├── tests/                         # Unit tests
└── requirements.txt               # Python dependencies
```

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | **Yes** | Gemini API key (or use Groq equivalent) |
| `NEWS_API_KEY` | No | Optional NewsAPI key for enhanced sentiment data |

---

*Built for advanced equity research automation.*
