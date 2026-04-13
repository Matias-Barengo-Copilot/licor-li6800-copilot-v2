#!/bin/bash
# Start Program IQ — runs backend + frontend together
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "🎮  Program IQ — Urban Arts Intelligence Dashboard"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start FastAPI backend
echo "▶ Starting API backend (port 8000)…"
cd "$ROOT"
python3 server.py &
BACKEND_PID=$!

# Wait for backend to be ready
echo "  Waiting for backend…"
for i in $(seq 1 20); do
  if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "  ✅ Backend ready"
    break
  fi
  sleep 1
done

# Start Next.js frontend
echo ""
echo "▶ Starting frontend (port 3000)…"
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Dashboard:  http://localhost:3000"
echo "  API docs:   http://localhost:8000/docs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Press Ctrl+C to stop both servers."
echo ""

# Wait and clean up
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait $BACKEND_PID $FRONTEND_PID
