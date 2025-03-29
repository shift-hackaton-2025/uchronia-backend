#!/bin/bash
# Change to the directory containing your app code
cd "$(dirname "$0")"
echo "Starting Uvicorn server..."
uvicorn api.main:app --host 0.0.0.0 --port 8000