# AI Timebox Backend

Cognitive Calendar API - Human-state aware time orchestration.

## Setup

1. Create virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:
```bash
pip install -e .
```

3. Copy and configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

4. Start PostgreSQL and Redis (via Docker or locally)

5. Run the server:
```bash
uvicorn app.main:app --reload
```

## API Docs

Once running, visit: http://localhost:8000/docs

## Architecture

See `/implementation_plan.md` in the artifacts directory for full architecture documentation.
