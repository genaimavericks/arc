#!/bin/bash

# Print banner
echo "Stopping RSW processes..."

# Find and kill Python processes
echo "Finding and killing Python processes..."
PYTHON_PIDS=$(ps -ef | grep python | grep -v grep | awk '{print $2}')
if [ -n "$PYTHON_PIDS" ]; then
    echo "Found Python processes with PIDs: $PYTHON_PIDS"
    echo "Killing Python processes..."
    kill -9 $PYTHON_PIDS
    echo "Python processes killed."
else
    echo "No Python processes found."
fi

# Stop Python API server (as a backup method)
echo "Stopping Python API server..."
pkill -f "python -m api.run" || echo "No API server running"

# Stop Next.js development server if running
echo "Stopping Next.js development server if running..."
pkill -f "node .*/rsw/node_modules/.bin/next" || echo "No Next.js server running"

echo "All RSW processes stopped."
