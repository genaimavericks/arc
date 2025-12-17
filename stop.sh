#!/bin/bash

# Print banner
echo "Stopping Lightening processes..."

# Stop Python API server
echo "Stopping Python API server..."
pkill -f "python -m api.run" || echo "No API server running" 

# Stop Next.js development server if running
echo "Stopping Next.js development server if running..."
pkill -f "node .*/arc/node_modules/.bin/next" || echo "No Next.js server running"

# Stop processes on specific ports (especially 9090 for GraphCypherQAChain)
echo "Stopping processes on port 9090..."
PORT_PIDS=$(lsof -ti :9090 2>/dev/null)
if [ -n "$PORT_PIDS" ]; then
    echo "Found processes on port 9090: $PORT_PIDS"
    kill $PORT_PIDS 2>/dev/null || true
    sleep 1
    # Force kill if still running
    PORT_PIDS=$(lsof -ti :9090 2>/dev/null)
    if [ -n "$PORT_PIDS" ]; then
        echo "Force killing processes on port 9090: $PORT_PIDS"
        kill -9 $PORT_PIDS 2>/dev/null || true
    fi
else
    echo "No processes found on port 9090"
fi

# Stop any uvicorn/fastapi processes related to Lightening
echo "Stopping any remaining uvicorn/fastapi processes..."
UVICORN_PIDS=$(ps aux | grep -E "[u]vicorn.*api\.run|[p]ython.*api\.run" | awk '{print $2}')
if [ -n "$UVICORN_PIDS" ]; then
    echo "Found uvicorn processes: $UVICORN_PIDS"
    kill $UVICORN_PIDS 2>/dev/null || true
    sleep 1
    # Force kill if still running
    UVICORN_PIDS=$(ps aux | grep -E "[u]vicorn.*api\.run|[p]ython.*api\.run" | awk '{print $2}')
    if [ -n "$UVICORN_PIDS" ]; then
        echo "Force killing uvicorn processes: $UVICORN_PIDS"
        kill -9 $UVICORN_PIDS 2>/dev/null || true
    fi
else
    echo "No uvicorn processes found"
fi

# Final verification
LIGHTENING_PIDS=$(ps aux | grep -E "[p]ython.*arc|[u]vicorn.*arc|[n]ode.*next" | awk '{print $2}')
if [ -n "$LIGHTENING_PIDS" ]; then
    echo "WARNING: Some Lightening processes may still be running: $LIGHTENING_PIDS"
    echo "Force killing all remaining Lightening processes"
    kill -9 $LIGHTENING_PIDS 2>/dev/null || true
fi

echo "All Lightening processes stopped."
