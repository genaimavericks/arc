#!/bin/bash

# Print banner
echo "Stopping Lightening processes..."

# Stop Python API server
echo "Stopping Python API server..."
pkill -f "python -m api.run" || echo "No API server running"

# Stop Next.js development server if running
echo "Stopping Next.js development server if running..."
pkill -f "node .*/arc/node_modules/.bin/next" || echo "No Next.js server running"

echo "All Lightening processes stopped."
