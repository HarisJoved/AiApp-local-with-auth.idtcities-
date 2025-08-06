#!/usr/bin/env python3
"""
Simple script to start the FastAPI backend server.
Run this from the project root directory.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Check if we're in the right directory
    if not Path("backend").exists():
        print("❌ Error: Please run this script from the project root directory")
        print("   Make sure you can see the 'backend' folder")
        sys.exit(1)
    
    # Change to backend directory
    os.chdir("backend")
    
    # Check if virtual environment exists
    venv_path = Path("venv")
    if not venv_path.exists():
        print("📦 Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("✅ Virtual environment created")
    
    # Determine the activation script path based on OS
    if os.name == 'nt':  # Windows
        activate_script = venv_path / "Scripts" / "activate.bat"
        python_path = venv_path / "Scripts" / "python.exe"
        pip_path = venv_path / "Scripts" / "pip.exe"
    else:  # Unix/Linux/macOS
        activate_script = venv_path / "bin" / "activate"
        python_path = venv_path / "bin" / "python"
        pip_path = venv_path / "bin" / "pip"
    
    # Install dependencies if needed
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        print("📋 Installing/updating dependencies...")
        subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], check=True)
        print("✅ Dependencies installed")
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  Warning: No .env file found. You may need to configure API keys.")
        print("   Copy .env.example to .env and fill in your API keys")
    
    print("\n🚀 Starting FastAPI server...")
    print("   Server will be available at: http://localhost:8000")
    print("   API docs will be available at: http://localhost:8000/docs")
    print("   Press Ctrl+C to stop the server\n")
    
    # Start the server
    try:
        subprocess.run([
            str(python_path), "-m", "uvicorn", 
            "app.main:app", 
            "--reload", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()