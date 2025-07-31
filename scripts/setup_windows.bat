@echo off
echo Document Embedding Platform Setup - Windows
echo ==========================================

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

REM Create necessary directories
echo Creating directories...
if not exist "backend\config" mkdir backend\config
if not exist "backend\logs" mkdir backend\logs
if not exist "backend\uploads" mkdir backend\uploads
if not exist "docs\images" mkdir docs\images
echo Directories created!

REM Setup backend
echo.
echo Setting up backend...
cd backend

REM Create virtual environment
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        echo Make sure Python is installed and added to PATH
        pause
        exit /b 1
    )
)

REM Activate virtual environment and install dependencies
echo Installing Python dependencies...
call venv\Scripts\activate
pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install Python dependencies
    pause
    exit /b 1
)

REM Create .env file
if not exist ".env" (
    if exist ".env.example" (
        echo Creating .env file from example...
        copy .env.example .env
    )
)

cd ..

REM Setup frontend
echo.
echo Setting up frontend...
cd frontend

REM Install Node.js dependencies
echo Installing Node.js dependencies...
call npm install
if errorlevel 1 (
    echo Error: Failed to install Node.js dependencies
    echo Make sure Node.js and npm are installed
    pause
    exit /b 1
)

REM Create .env file
if not exist ".env" (
    if exist ".env.example" (
        echo Creating .env file from example...
        copy .env.example .env
    )
)

cd ..

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Configure your embedder and vector database in backend\.env
echo 2. Run start_windows.bat to start both servers
echo 3. Open http://localhost:3000 in your browser
echo.
pause 