#!/bin/bash

# Start script for Audiobook Feed Generator Web UI

# Get the script directory at the beginning
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Function to check if a process is running on a specific port
check_port() {
  if netstat -tuln | grep -q ":$1 "; then
    return 0  # Port is in use
  else
    return 1  # Port is free
  fi
}

# Start backend server
echo "Starting backend server..."
cd "$(dirname "$0")/src/web/backend"

# Check if backend is already running
if check_port 5005; then
  echo "Backend server already running on port 5005"
else
  nohup npm start > ../../../logs/backend.log 2>&1 &
  echo "Backend server started on http://localhost:5005"
fi

# Start frontend development server
echo "Starting frontend development server..."
cd ../frontend

# Check if frontend is already running
if check_port 5006; then
  echo "Frontend server already running on port 5006"
else
  nohup npm run serve > ../../../logs/frontend.log 2>&1 &
  echo "Frontend server started on http://localhost:5006"
fi

echo ""
echo "Application is running!"
echo "- Frontend: http://localhost:5006"
echo "- Backend: http://localhost:5005"
echo ""
echo "You can check the logs in:"
echo "- Backend log: logs/backend.log"
echo "- Frontend log: logs/frontend.log"
echo ""
echo "Opening the application in your browser..."
# Try to open the browser automatically
if [ -f "$SCRIPT_DIR/open_web_ui.sh" ]; then
    "$SCRIPT_DIR/open_web_ui.sh"
else
    echo "Note: open_web_ui.sh not found, please manually open: http://localhost:5006"
fi
