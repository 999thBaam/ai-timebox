# AI Timebox

A human-state–aware time orchestration system that models cognitive load, emotional residue, volatility, and uncertainty to make scheduling decisions that feel humane, calm, and intelligent.

## Project Structure

```
ai-timebox/
├── frontend/          # Next.js web application
│   └── src/
│       └── app/       # App Router pages
│
├── backend/           # FastAPI Python backend
│   └── app/
│       ├── api/       # REST API endpoints
│       ├── core/      # Configuration
│       ├── db/        # Database models & session
│       ├── models/    # Domain models (IHF 2.0, HumanState, etc.)
│       └── services/  # Business logic (LLM, Question Policy)
│
└── docs/              # Architecture documentation
```

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# Edit .env with your LLM API key
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Core Concepts

- **Intent Hypothesis Framework (IHF 2.0)**: Every input becomes a hypothesis, not an action
- **Human State Model**: Tracks cognitive load, energy, fragility, context residue
- **Safety Policies**: Protective constraints that decay over time
- **Question Policy**: Asks only when VOI > COI (Value of Information > Cost of Interruption)

## Philosophy

AI Timebox does not try to make users do more. It ensures that what they do, they can actually carry.

This is not productivity software. This is **cognitive infrastructure**.
