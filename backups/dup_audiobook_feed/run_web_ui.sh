#!/bin/bash

# One-command script to set up and run the Audiobook Feed Generator Web UI

echo "===== Audiobook Feed Generator Web UI ====="

# Check if setup has been run before
if [ ! -d "src/web/backend/node_modules" ] || [ ! -d "src/web/frontend/node_modules" ]; then
  echo "First-time setup detected. Installing dependencies..."
  ./setup_web_ui.sh
fi

# Start the application
echo "Starting the application..."
./start_web_ui.sh

echo ""
echo "Press Ctrl+C when you're ready to stop the application."
echo "Or run ./stop_web_ui.sh in another terminal."
echo ""

# Wait for user to press Ctrl+C
trap "echo 'Stopping application...'; ./stop_web_ui.sh" INT
while true; do
  sleep 1
done
