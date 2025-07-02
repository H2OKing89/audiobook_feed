#!/bin/bash

# Stop script for Audiobook Feed Generator Web UI
# SAFETY-FOCUSED version that won't kill SSH sessions

echo "Stopping Audiobook Feed Generator Web UI (SAFE MODE)..."

# Function to safely kill process running on specific port
# Only kills Node.js processes to avoid terminating SSH or other critical services
kill_port() {
  PORT=$1
  echo "Looking for Node.js processes on port $PORT..."
  
  # Look ONLY for node processes on this port and exclude SSH
  # The grep -v excludes SSH, grep node only includes node processes
  PIDS=$(lsof -ti:$PORT | grep -v sshd | xargs -r ps -o pid= -p 2>/dev/null | xargs -r)
  
  if [ -n "$PIDS" ]; then
    echo "Found processes on port $PORT: $PIDS"
    
    # Process each PID individually with extra safety checks
    for PID in $PIDS; do
      # Extra verification - get full command line to ensure it's Node.js related
      CMDLINE=$(cat /proc/$PID/cmdline 2>/dev/null | tr '\0' ' ' || echo "")
      PROCESS_NAME=$(ps -p $PID -o comm= 2>/dev/null || echo "")
      
      # Only proceed if it's definitely a Node.js process
      if [[ "$PROCESS_NAME" == *"node"* || "$CMDLINE" == *"node"* || 
            "$PROCESS_NAME" == *"npm"* || "$CMDLINE" == *"npm"* || 
            "$PROCESS_NAME" == *"vue"* || "$CMDLINE" == *"vue"* ]]; then
            
        echo "✓ Confirmed Node.js process: $PID ($PROCESS_NAME)"
        echo "  Command: ${CMDLINE:0:80}..."
        
        # Try gentle termination first
        echo "  Sending SIGTERM..."
        kill -15 $PID 2>/dev/null
        
        # Wait briefly to see if it shuts down
        sleep 2
        
        # Check if still running, then force kill
        if kill -0 $PID 2>/dev/null; then
          echo "  Process still running, sending SIGKILL..."
          kill -9 $PID 2>/dev/null
        else
          echo "  Process terminated successfully."
        fi
      else
        echo "⚠️ Skipping non-Node.js process: $PID ($PROCESS_NAME)"
      fi
    done
  else
    echo "No Node.js processes found on port $PORT"
  fi
}

# First, try stopping by port (safest method)
echo "Step 1: Stopping frontend server (Vue.js on port 5007)..."
kill_port 5007

echo "Step 2: Stopping backend server (Express on port 5005)..."
kill_port 5005

# Also try backup method - find processes by command pattern
echo "Step 3: Checking for any remaining Node.js Web UI processes..."

# Find Vue CLI service processes
echo "Looking for Vue CLI processes..."
VUE_PIDS=$(pgrep -f "vue-cli-service" 2>/dev/null || echo "")
if [ -n "$VUE_PIDS" ]; then
  for PID in $VUE_PIDS; do
    CMDLINE=$(cat /proc/$PID/cmdline 2>/dev/null | tr '\0' ' ' || echo "")
    if [[ "$CMDLINE" == *"vue-cli-service"* && "$CMDLINE" != *"ssh"* ]]; then
      echo "Found Vue process to stop: $PID"
      echo "  Command: ${CMDLINE:0:80}..."
      kill -15 $PID 2>/dev/null
      sleep 2
      if kill -0 $PID 2>/dev/null; then
        kill -9 $PID 2>/dev/null
      fi
    fi
  done
else
  echo "No Vue CLI processes found."
fi

# Find app.js processes
echo "Looking for Node.js backend processes..."
BACKEND_PIDS=$(pgrep -f "node.*app.js" 2>/dev/null || echo "")
if [ -n "$BACKEND_PIDS" ]; then
  for PID in $BACKEND_PIDS; do
    CMDLINE=$(cat /proc/$PID/cmdline 2>/dev/null | tr '\0' ' ' || echo "")
    if [[ "$CMDLINE" == *"app.js"* && "$CMDLINE" != *"ssh"* ]]; then
      echo "Found backend process to stop: $PID"
      echo "  Command: ${CMDLINE:0:80}..."
      kill -15 $PID 2>/dev/null
      sleep 2
      if kill -0 $PID 2>/dev/null; then
        kill -9 $PID 2>/dev/null
      fi
    fi
  done
else
  echo "No backend processes found."
fi

echo "Web UI has been safely stopped."
echo "SSH session should remain active and unaffected."
