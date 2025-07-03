#!/bin/bash

# Ultra-safe script to stop Audiobook Feed Generator Web UI
# This version takes extreme precautions to NEVER affect SSH sessions

echo "Stopping Audiobook Feed Generator Web UI (ULTRA-SAFE MODE)..."

# Get the current user's username for safer process identification
CURRENT_USER=$(whoami)
echo "Running as user: $CURRENT_USER"

# Function to check if a process is definitely a web UI process
is_web_ui_process() {
  local PID=$1
  
  # Skip if we can't access the process info (might be system or other user's process)
  if [ ! -r "/proc/$PID/cmdline" ]; then
    return 1 # Not our process
  fi
  
  # Get command line and executable name
  local CMDLINE=$(tr '\0' ' ' < /proc/$PID/cmdline 2>/dev/null)
  local PROCESS_NAME=$(ps -p $PID -o comm= 2>/dev/null)
  local PROCESS_USER=$(ps -p $PID -o user= 2>/dev/null)
  
  # Skip any process not owned by the current user
  if [ "$PROCESS_USER" != "$CURRENT_USER" ]; then
    return 1 # Not our process
  fi
  
  # NEVER touch SSH-related processes - multiple checks
  if [[ "$CMDLINE" == *"ssh"* || "$PROCESS_NAME" == *"ssh"* || 
        "$CMDLINE" == *"vscode"* || "$PROCESS_NAME" == *"vscode"* ||
        "$CMDLINE" == *"code"* ]]; then
    echo "⚠️ Skipping SSH/VSCode-related process: $PID"
    return 1 # Not a web UI process
  fi
  
  # Check if it's a Node.js/npm/Vue process with specific web UI patterns
  if [[ "$PROCESS_NAME" == *"node"* || "$CMDLINE" == *"node"* ]]; then
    # Only target specific web UI processes
    if [[ "$CMDLINE" == *"vue-cli-service"* || 
          "$CMDLINE" == *"frontend"* ||
          "$CMDLINE" == *"backend"* || 
          "$CMDLINE" == *"app.js"* || 
          "$CMDLINE" == *"express"* || 
          "$CMDLINE" == *":5005"* || 
          "$CMDLINE" == *":5007"* ]]; then
      return 0 # Yes, it's a web UI process
    fi
  fi
  
  return 1 # Not a web UI process
}

# Find our specific web UI processes safely
echo "Searching for web UI processes (Vue.js and Express)..."
echo "This will ONLY target processes matching specific patterns in our web UI"

# Find potential Node.js processes
WEB_UI_PIDS=()
for PID in $(pgrep -u $CURRENT_USER 'node|npm|vue' 2>/dev/null); do
  if is_web_ui_process $PID; then
    WEB_UI_PIDS+=($PID)
    CMDLINE=$(tr '\0' ' ' < /proc/$PID/cmdline 2>/dev/null | cut -c 1-80)
    echo "✓ Found web UI process $PID: $CMDLINE..."
  fi
done

# If no processes found, check using port information specifically for Vue/Express
if [ ${#WEB_UI_PIDS[@]} -eq 0 ]; then
  echo "No web UI processes found by name, checking ports 5005 and 5007..."
  
  # Check port 5005 (Express backend)
  for PID in $(lsof -t -i:5005 -sTCP:LISTEN 2>/dev/null); do
    if is_web_ui_process $PID; then
      WEB_UI_PIDS+=($PID)
      CMDLINE=$(tr '\0' ' ' < /proc/$PID/cmdline 2>/dev/null | cut -c 1-80)
      echo "✓ Found backend process $PID on port 5005: $CMDLINE..."
    fi
  done
  
  # Check port 5007 (Vue frontend)
  for PID in $(lsof -t -i:5007 -sTCP:LISTEN 2>/dev/null); do
    if is_web_ui_process $PID; then
      WEB_UI_PIDS+=($PID)
      CMDLINE=$(tr '\0' ' ' < /proc/$PID/cmdline 2>/dev/null | cut -c 1-80)
      echo "✓ Found frontend process $PID on port 5007: $CMDLINE..."
    fi
  done
fi

# Stop the processes
if [ ${#WEB_UI_PIDS[@]} -eq 0 ]; then
  echo "No AudioStacker web UI processes found to stop."
else
  echo "Found ${#WEB_UI_PIDS[@]} web UI processes to stop..."
  
  for PID in "${WEB_UI_PIDS[@]}"; do
    echo "Stopping process $PID..."
    
    # Get process info for logging
    PS_INFO=$(ps -p $PID -o pid,comm,args 2>/dev/null || echo "Process $PID")
    echo "Process details: $PS_INFO"
    
    # Send SIGTERM first for graceful shutdown
    kill -15 $PID 2>/dev/null
    echo "Sent SIGTERM to process $PID"
    
    # Wait a moment for graceful termination
    sleep 2
    
    # Check if still running
    if kill -0 $PID 2>/dev/null; then
      echo "Process $PID still running, sending SIGKILL..."
      kill -9 $PID 2>/dev/null
    else
      echo "Process $PID terminated successfully."
    fi
  done
fi

echo "Web UI shutdown process completed."
