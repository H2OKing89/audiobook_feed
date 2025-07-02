#!/bin/bash

# Start script for Audiobook Feed Generator Web UI

# Get the script directory at the beginning
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Ensure log directory exists
mkdir -p "$SCRIPT_DIR/logs"

# Function to check if a process is running on a specific port
check_port() {
  if command -v netstat >/dev/null; then
    if netstat -tuln | grep -q ":$1 "; then
      return 0  # Port is in use
    else
      return 1  # Port is free
    fi
  elif command -v lsof >/dev/null; then
    if lsof -i:"$1" -sTCP:LISTEN >/dev/null 2>&1; then
      return 0  # Port is in use
    else
      return 1  # Port is free
    fi
  else
    echo "Warning: netstat and lsof not found, cannot check port $1"
    return 1  # Assume port is free
  fi
}

# Function to wait for a service to be available
wait_for_service() {
  local port=$1
  local name=$2
  local max_attempts=$3
  local wait_time=$4
  
  echo "Waiting for $name to start on port $port..."
  
  for ((i=1; i<=max_attempts; i++)); do
    if check_port "$port"; then
      echo "$name is now available on port $port"
      return 0
    fi
    echo "Waiting for $name... ($i/$max_attempts)"
    sleep "$wait_time"
  done
  
  echo "Warning: $name did not start within expected time"
  return 1
}

# Start backend server
echo "Starting backend server..."
cd "$SCRIPT_DIR/src/web/backend"

# Check if backend is already running
if check_port 5005; then
  echo "Backend server already running on port 5005"
else
  # Make sure node_modules exists
  if [ ! -d "node_modules" ]; then
    echo "Installing backend dependencies..."
    npm install
  fi
  
  echo "Starting backend server..."
  nohup npm start > "$SCRIPT_DIR/logs/backend.log" 2>&1 &
  echo "Backend server started with PID $!"
  
  # Wait for backend to be available
  wait_for_service 5005 "Backend server" 10 2
fi

# Start frontend development server
echo "Starting frontend development server..."
cd "$SCRIPT_DIR/src/web/frontend"

# Check if frontend is already running
if check_port 5006; then
  echo "Frontend server already running on port 5006"
else
  # Make sure node_modules exists
  if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
  fi
  
  echo "Starting frontend server..."
  nohup npm run serve > "$SCRIPT_DIR/logs/frontend.log" 2>&1 &
  echo "Frontend server started with PID $!"
  
  # Wait for frontend to be available
  wait_for_service 5006 "Frontend server" 20 2
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
