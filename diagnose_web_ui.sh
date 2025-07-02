#!/bin/bash

# Script to check, diagnose, and fix issues with the Web UI
echo "AudioStacker Web UI Diagnostics"
echo "=============================="
echo ""

# 1. Check if backend is running
echo "Checking backend (port 5005)..."
BACKEND_PID=$(lsof -i:5005 -t 2>/dev/null)

if [ -n "$BACKEND_PID" ]; then
  echo "✅ Backend is running (PID: $BACKEND_PID)"
else
  echo "❌ Backend is not running"
  echo "Checking for errors in backend.log..."
  BACKEND_ERRORS=$(grep -i "error\|exception\|fail" /home/quentin/dev/audiobook_feed/logs/backend.log | tail -n 10)
  if [ -n "$BACKEND_ERRORS" ]; then
    echo "Found recent errors:"
    echo "$BACKEND_ERRORS"
  else
    echo "No obvious errors found in backend.log"
  fi
fi

# 2. Check if frontend is running
echo ""
echo "Checking frontend (port 5006)..."
FRONTEND_PID=$(lsof -i:5006 -t 2>/dev/null)

if [ -n "$FRONTEND_PID" ]; then
  echo "✅ Frontend is running (PID: $FRONTEND_PID)"
else
  echo "❌ Frontend is not running"
  echo "Checking for errors in frontend.log..."
  FRONTEND_ERRORS=$(grep -i "error\|exception\|fail" /home/quentin/dev/audiobook_feed/logs/frontend.log | tail -n 10)
  if [ -n "$FRONTEND_ERRORS" ]; then
    echo "Found recent errors:"
    echo "$FRONTEND_ERRORS"
  else
    echo "No obvious errors found in frontend.log"
  fi
fi

# 3. Check Node.js and npm installation
echo ""
echo "Checking Node.js and npm..."
NODE_VERSION=$(node --version 2>/dev/null)
NPM_VERSION=$(npm --version 2>/dev/null)

if [ -n "$NODE_VERSION" ]; then
  echo "✅ Node.js is installed: $NODE_VERSION"
else
  echo "❌ Node.js is not installed or not in PATH"
fi

if [ -n "$NPM_VERSION" ]; then
  echo "✅ npm is installed: $NPM_VERSION"
else
  echo "❌ npm is not installed or not in PATH"
fi

# 4. Check backend dependencies
echo ""
echo "Checking backend dependencies..."
if [ -f "/home/quentin/dev/audiobook_feed/src/web/backend/package.json" ]; then
  cd /home/quentin/dev/audiobook_feed/src/web/backend
  if [ -d "node_modules" ]; then
    echo "✅ Backend node_modules directory exists"
  else
    echo "❌ Backend node_modules directory missing"
    echo "Recommendation: Run 'npm install' in /src/web/backend directory"
  fi
else
  echo "❌ Backend package.json not found"
fi

# 5. Check frontend dependencies
echo ""
echo "Checking frontend dependencies..."
if [ -f "/home/quentin/dev/audiobook_feed/src/web/frontend/package.json" ]; then
  cd /home/quentin/dev/audiobook_feed/src/web/frontend
  if [ -d "node_modules" ]; then
    echo "✅ Frontend node_modules directory exists"
  else
    echo "❌ Frontend node_modules directory missing"
    echo "Recommendation: Run 'npm install' in /src/web/frontend directory"
  fi
else
  echo "❌ Frontend package.json not found"
fi

# 6. Check database file
echo ""
echo "Checking database file..."
if [ -f "/home/quentin/dev/audiobook_feed/src/audiostracker/audiobooks.db" ]; then
  DB_SIZE=$(ls -lh /home/quentin/dev/audiobook_feed/src/audiostracker/audiobooks.db | awk '{print $5}')
  echo "✅ Database file exists (Size: $DB_SIZE)"
  
  # Check if sqlite3 is installed for database diagnostics
  if command -v sqlite3 > /dev/null; then
    echo "Running basic database diagnostics..."
    echo "- Number of audiobooks: $(sqlite3 /home/quentin/dev/audiobook_feed/src/audiostracker/audiobooks.db "SELECT COUNT(*) FROM audiobooks;")"
    echo "- Number of watchlist entries: $(sqlite3 /home/quentin/dev/audiobook_feed/src/audiostracker/audiobooks.db "SELECT COUNT(*) FROM watchlist WHERE active=1;")"
  else
    echo "sqlite3 not installed, skipping database diagnostics"
  fi
else
  echo "❌ Database file not found"
  echo "Recommendation: Run the application once to initialize the database"
fi

# 7. Recommendations
echo ""
echo "Recommendations:"
echo "---------------"

if [ -z "$BACKEND_PID" ] || [ -z "$FRONTEND_PID" ]; then
  echo "1. Try manually starting the services:"
  echo "   - Backend: cd /home/quentin/dev/audiobook_feed/src/web/backend && npm start"
  echo "   - Frontend: cd /home/quentin/dev/audiobook_feed/src/web/frontend && npm run serve"
  echo ""
  echo "2. Check for any dependency issues:"
  echo "   - Backend: cd /home/quentin/dev/audiobook_feed/src/web/backend && npm install"
  echo "   - Frontend: cd /home/quentin/dev/audiobook_feed/src/web/frontend && npm install"
  echo ""
  echo "3. Monitor the logs while starting services:"
  echo "   - tail -f /home/quentin/dev/audiobook_feed/logs/backend.log"
  echo "   - tail -f /home/quentin/dev/audiobook_feed/logs/frontend.log"
fi

echo ""
echo "=============================="
