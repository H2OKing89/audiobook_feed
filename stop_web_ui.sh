#!/bin/bash

# Stop script for Audiobook Feed Generator Web UI

echo "Stopping Audiobook Feed Generator Web UI..."

# Function to safely kill process running on specific port
# Only kills Node.js processes to avoid terminating SSH or other critical services
kill_port() {
  PORT=$1
  # Only target Node.js processes running on the specific port
  PID=$(lsof -ti:$PORT -c node)
  
  if [ -n "$PID" ]; then
    echo "Found Node.js process on port $PORT (PID: $PID)"
    
    # Check if this is really a Web UI process
    PROCESS_INFO=$(ps -p $PID -o command= || echo "")
    
    if [[ "$PROCESS_INFO" == *"node"* && ("$PROCESS_INFO" == *"vue"* || "$PROCESS_INFO" == *"app.js"*) ]]; then
      echo "Stopping process on port $PORT (PID: $PID)"
      # First try gentle termination
      kill -15 $PID
      
      # Wait briefly to see if it shuts down
      sleep 1
      
      # Check if still running, then force kill
      if kill -0 $PID 2>/dev/null; then
        echo "Process didn't terminate gracefully, forcing shutdown"
        kill -9 $PID
      fi
      
      return 0
    else
      echo "Warning: Process on port $PORT doesn't appear to be part of the Web UI. Skipping."
      return 1
    fi
  else
    echo "No Node.js process found running on port $PORT"
    return 1
  fi
}

echo "Stopping frontend server (Vue.js on port 5006)..."
kill_port 5006

echo "Stopping backend server (Express on port 5005)..."
kill_port 5005

# Also try to find and kill any related processes by name
echo "Checking for any remaining Web UI processes..."

# Find and kill frontend processes (Vue CLI service)
VUE_PIDS=$(pgrep -f "vue-cli-service serve" || echo "")
if [ -n "$VUE_PIDS" ]; then
  echo "Found additional frontend processes: $VUE_PIDS"
  for PID in $VUE_PIDS; do
    echo "Stopping Vue process (PID: $PID)"
    kill -15 $PID
  done
fi

# Find and kill backend processes (Node.js running app.js)
BACKEND_PIDS=$(pgrep -f "node.*app.js" || echo "")
if [ -n "$BACKEND_PIDS" ]; then
  echo "Found additional backend processes: $BACKEND_PIDS"
  for PID in $BACKEND_PIDS; do
    echo "Stopping backend process (PID: $PID)"
    kill -15 $PID
  done
fi

echo "Web UI has been stopped."
