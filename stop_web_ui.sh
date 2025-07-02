#!/bin/bash

# Stop script for Audiobook Feed Generator Web UI

echo "Stopping Audiobook Feed Generator Web UI..."

# Function to safely kill process running on specific port
# Only kills Node.js processes to avoid terminating SSH or other critical services
kill_port() {
  PORT=$1
  # Only target Node.js processes running on the specific port
  # Use -F to format output as a single PID per line
  PIDS=$(lsof -ti:$PORT | grep -v sshd)
  
  if [ -n "$PIDS" ]; then
    echo "Found processes on port $PORT"
    
    # Process each PID individually
    for PID in $PIDS; do
      # Get process command name
      PROCESS_CMD=$(ps -p $PID -o comm= 2>/dev/null || echo "")
      
      # Only kill Node.js processes or processes related to our web UI
      if [[ "$PROCESS_CMD" == *"node"* || "$PROCESS_CMD" == *"npm"* || "$PROCESS_CMD" == *"vue"* ]]; then
        echo "Stopping process on port $PORT (PID: $PID, Command: $PROCESS_CMD)"
        # First try gentle termination
        kill -15 $PID 2>/dev/null
        
        # Wait briefly to see if it shuts down
        sleep 1
        
        # Check if still running, then force kill
        if kill -0 $PID 2>/dev/null; then
          echo "Process didn't terminate gracefully, forcing shutdown"
          kill -9 $PID 2>/dev/null
        fi
      else
        echo "Skipping non-Web UI process on port $PORT (PID: $PID, Command: $PROCESS_CMD)"
      fi
    done
    
    return 0
  else
    echo "No processes found running on port $PORT"
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
# Make sure to exclude SSH sessions
VUE_PIDS=$(pgrep -f "vue-cli-service serve" 2>/dev/null || echo "")
if [ -n "$VUE_PIDS" ]; then
  echo "Found additional frontend processes"
  for PID in $VUE_PIDS; do
    # Double-check that this is actually a Vue process
    PROCESS_CMD=$(ps -p $PID -o comm= 2>/dev/null || echo "")
    if [[ "$PROCESS_CMD" == *"node"* ]]; then
      echo "Stopping Vue process (PID: $PID)"
      kill -15 $PID 2>/dev/null
      sleep 1
      # Force kill if still running
      if kill -0 $PID 2>/dev/null; then
        kill -9 $PID 2>/dev/null
      fi
    fi
  done
fi

# Find and kill backend processes (Node.js running app.js)
BACKEND_PIDS=$(pgrep -f "node.*app.js" 2>/dev/null || echo "")
if [ -n "$BACKEND_PIDS" ]; then
  echo "Found additional backend processes"
  for PID in $BACKEND_PIDS; do
    # Double-check that this is actually a Node process
    PROCESS_CMD=$(ps -p $PID -o comm= 2>/dev/null || echo "")
    if [[ "$PROCESS_CMD" == *"node"* ]]; then
      echo "Stopping backend process (PID: $PID)"
      kill -15 $PID 2>/dev/null
      sleep 1
      # Force kill if still running
      if kill -0 $PID 2>/dev/null; then
        kill -9 $PID 2>/dev/null
      fi
    fi
  done
fi

echo "Web UI has been stopped."
