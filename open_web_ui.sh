#!/bin/bash

# Script to open the Audiobook Feed UI in the default browser

echo "Opening Audiobook Feed Generator Web UI in your browser..."

# Function to detect the operating system and open URL accordingly
open_url() {
    URL=$1
    
    # Try to detect the OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v xdg-open > /dev/null; then
            xdg-open "$URL"
        else
            echo "Cannot open browser automatically. Please open this URL manually: $URL"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open "$URL"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        # Windows
        start "$URL"
    else
        echo "Cannot open browser automatically. Please open this URL manually: $URL"
    fi
}

# Wait a moment to ensure services are running
sleep 2

# Open the frontend URL
open_url "http://localhost:5006"

echo "If the browser didn't open automatically, please visit: http://localhost:5006"
