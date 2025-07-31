#!/bin/bash

# Document Embedding Platform - Start Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Document Embedding Platform${NC}"
echo "========================================"

# Check if we're in the right directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}❌ Please run this script from the project root directory${NC}"
    exit 1
fi

# Function to start backend
start_backend() {
    echo -e "${YELLOW}Starting backend server...${NC}"
    cd backend
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo -e "${RED}❌ Virtual environment not found. Please run setup.py first.${NC}"
        exit 1
    fi
    
    # Activate virtual environment and start server
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows
        source venv/Scripts/activate
    else
        # Unix/Linux/macOS
        source venv/bin/activate
    fi
    
    echo -e "${GREEN}✓ Backend virtual environment activated${NC}"
    
    # Start FastAPI server
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    
    echo -e "${GREEN}✓ Backend server started (PID: $BACKEND_PID)${NC}"
    cd ..
}

# Function to start frontend
start_frontend() {
    echo -e "${YELLOW}Starting frontend development server...${NC}"
    cd frontend
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo -e "${RED}❌ Node modules not found. Please run setup.py first.${NC}"
        exit 1
    fi
    
    # Start React development server
    npm start &
    FRONTEND_PID=$!
    
    echo -e "${GREEN}✓ Frontend server started (PID: $FRONTEND_PID)${NC}"
    cd ..
}

# Function to handle cleanup
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        echo -e "${GREEN}✓ Backend server stopped${NC}"
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        echo -e "${GREEN}✓ Frontend server stopped${NC}"
    fi
    
    echo -e "${BLUE}👋 Goodbye!${NC}"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# Start servers
start_backend
sleep 2
start_frontend

echo -e "\n${GREEN}🎉 Both servers are starting up!${NC}"
echo -e "${BLUE}📍 Backend API: http://localhost:8000${NC}"
echo -e "${BLUE}📍 Frontend App: http://localhost:3000${NC}"
echo -e "${BLUE}📍 API Documentation: http://localhost:8000/docs${NC}"
echo -e "\n${YELLOW}Press Ctrl+C to stop both servers${NC}"

# Wait for user interrupt
wait 