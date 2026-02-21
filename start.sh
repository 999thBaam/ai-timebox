#!/bin/bash
# AI Timebox - Start both backend and frontend
set -e

echo "=== AI Timebox ==="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Start backend
echo -e "${GREEN}Starting backend...${NC}"
cd "$(dirname "$0")/backend"

if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -e . 2>/dev/null || pip install -q fastapi uvicorn pydantic pydantic-settings sqlalchemy asyncpg redis httpx python-dotenv 2>/dev/null

echo -e "${GREEN}Backend starting on http://localhost:8000${NC}"
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
echo -e "${BLUE}Starting frontend...${NC}"
cd "$(dirname "$0")/frontend"

if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo -e "${BLUE}Frontend starting on http://localhost:3000${NC}"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "============================================"
echo -e "  ${GREEN}Backend:${NC}  http://localhost:8000"
echo -e "  ${BLUE}Frontend:${NC} http://localhost:3000"
echo -e "  ${GREEN}API Docs:${NC} http://localhost:8000/docs"
echo "============================================"
echo ""
echo "Press Ctrl+C to stop both servers"

# Handle cleanup
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for either process to exit
wait
