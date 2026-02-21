# AI Timebox

A human-state-aware time orchestration system that models cognitive load, emotional residue, volatility, and uncertainty to make scheduling decisions that feel humane, calm, and intelligent.

## Quick Start

The fastest way to get running:

```bash
# 1. Start the backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy asyncpg redis httpx python-dotenv
uvicorn app.main:app --reload --port 8000

# 2. In another terminal, start the frontend
cd frontend
npm install
npm run dev
```

Then open **http://localhost:3000**

### LLM Configuration (Optional)

The app works out of the box with a built-in rule-based intent parser. For smarter parsing, add an OpenAI API key:

```bash
cd backend
echo 'LLM_API_KEY=your-key-here' >> .env
```

## How It Works

1. **Onboarding** - Answer 5 quick questions to calibrate your cognitive profile
2. **Schedule** - Type natural language like "Write code for 2 hours this morning"
3. **The system** parses your intent, checks your cognitive state, and finds the best time slot
4. **Safety** - It won't overload you. If scheduling something would push cognitive load too high, it rejects that slot
5. **Undo** - Every change can be undone

## Project Structure

```
ai-timebox/
├── start.sh              # Run both backend + frontend
├── frontend/             # Next.js web application
│   └── src/
│       ├── app/          # App Router pages
│       ├── components/   # React components
│       └── lib/          # API client
│
└── backend/              # FastAPI Python backend
    └── app/
        ├── api/          # REST API endpoints
        ├── core/         # Configuration
        ├── db/           # Database models & session
        ├── models/       # Domain models (IHF 2.0, HumanState, etc.)
        └── services/     # Business logic (LLM, Planner, Question Policy)
```

## Core Concepts

- **Intent Hypothesis Framework (IHF 2.0)**: Every input becomes a hypothesis, not an action
- **Human State Model**: Tracks cognitive load, energy, fragility, context residue (7 dimensions)
- **Safety Policies**: Protective constraints that decay over time
- **Question Policy**: Asks only when VOI > COI (Value of Information > Cost of Interruption)
- **Rule-Based Fallback**: Works without any LLM API key for basic scheduling

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/onboarding/questions` | GET | Get onboarding questionnaire |
| `/api/onboarding/submit` | POST | Submit answers, calibrate state |
| `/api/intents/parse` | POST | Parse scheduling request |
| `/api/intents/answer` | POST | Answer clarifying question |
| `/api/state/{user_id}` | GET | Get cognitive state summary |
| `/api/timeline/{user_id}` | GET | Get today's schedule |
| `/api/undo/{user_id}/history` | GET | Get undo history |
| `/api/undo/{user_id}/undo/{id}` | POST | Undo a change |
| `/health` | GET | Health check |

Interactive API docs at **http://localhost:8000/docs**

## Philosophy

AI Timebox does not try to make users do more. It ensures that what they do, they can actually carry.

This is not productivity software. This is **cognitive infrastructure**.
