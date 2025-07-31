@echo off
echo Starting Document Embedding Platform...
echo =======================================

REM Check if directories exist
if not exist "backend" (
    echo Error: backend directory not found
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

if not exist "frontend" (
    echo Error: frontend directory not found
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

REM Start backend server
echo Starting backend server...
start cmd /k "cd backend && venv\Scripts\activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

REM Wait a moment for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend server
echo Starting frontend server...
start cmd /k "cd frontend && npm start"

echo.
echo Both servers are starting up!
echo Backend API: http://localhost:8000
echo Frontend App: http://localhost:3000
echo API Documentation: http://localhost:8000/docs
echo.
echo Close both command windows to stop the servers
pause 