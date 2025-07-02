#!/bin/bash

# Safely stop the Audiobook Feed Generator Web UI
echo "Stopping Audiobook Feed Generator Web UI..."

# Function to safely kill a process running on a specific port
kill_process_on_port() {
  local port=$1
  local pid=$(lsof -i:$port -t 2>/dev/null)
  
  if [ -n "$pid" ]; then
    echo "Stopping process on port $port (PID: $pid)"
    # Send SIGTERM first, then only SIGKILL if necessary
    kill -15 $pid 2>/dev/null || true
    
    # Wait for a moment to let the process terminate gracefully
    sleep 1
    
    # Check if process is still running
    if ps -p $pid > /dev/null 2>&1; then
      echo "Process still running, forcing termination"
      kill -9 $pid 2>/dev/null || true
    fi
  else
    echo "No process found on port $port"
  fi
}

# Stop frontend (port 5006)
kill_process_on_port 5006

# Stop backend (port 5005)
kill_process_on_port 5005

echo "Web UI has been stopped."
