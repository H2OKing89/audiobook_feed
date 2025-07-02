#!/bin/bash

# Stop script for Audiobook Feed Generator Web UI

echo "Stopping Audiobook Feed Generator Web UI..."

# Function to kill process running on specific port
kill_port() {
  PORT=$1
  PID=$(lsof -ti:$PORT)
  if [ -n "$PID" ]; then
    echo "Killing process on port $PORT (PID: $PID)"
    kill $PID
    return 0
  else
    echo "No process found running on port $PORT"
    return 1
  fi
}

# Stop frontend server (on port 5006)
kill_port 5006

# Stop backend server (on port 5005)
kill_port 5005

echo "Web UI has been stopped."
