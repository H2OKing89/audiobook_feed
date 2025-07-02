#!/bin/bash

# Setup script for Audiobook Feed Generator Web UI

echo "===== Setting up Audiobook Feed Generator Web UI ====="

# Install backend dependencies
echo "Setting up backend..."
cd "$(dirname "$0")/src/web/backend"
npm install
echo "Backend setup complete!"

# Install frontend dependencies with specific fixes
echo "Setting up frontend..."
cd ../frontend
npm install
npm install @babel/eslint-parser --save-dev
echo "Frontend setup complete!"

echo "===== Setup completed! ====="
echo ""
echo "To start the application, run:"
echo "1. Backend: cd src/web/backend && npm start"
echo "2. Frontend: cd src/web/frontend && npm run serve"
echo ""
echo "Then open your browser to: http://localhost:5006"
