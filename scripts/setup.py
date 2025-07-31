#!/usr/bin/env python3
"""
Setup script for Document Embedding Platform
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, cwd=None):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True, 
            cwd=cwd
        )
        print(f"✓ {command}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"✗ {command}")
        print(f"Error: {e.stderr}")
        return None

def setup_backend():
    """Set up the backend environment"""
    print("\n🔧 Setting up backend...")
    
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("❌ Backend directory not found")
        return False
    
    # Create virtual environment
    venv_path = backend_dir / "venv"
    if not venv_path.exists():
        print("Creating Python virtual environment...")
        if not run_command("python -m venv venv", cwd=backend_dir):
            print("❌ Failed to create virtual environment")
            return False
    
    # Install dependencies
    print("Installing Python dependencies...")
    if sys.platform == "win32":
        pip_cmd = "venv\\Scripts\\pip install -r requirements.txt"
    else:
        pip_cmd = "venv/bin/pip install -r requirements.txt"
    
    if not run_command(pip_cmd, cwd=backend_dir):
        print("❌ Failed to install Python dependencies")
        return False
    
    # Copy environment file
    env_example = backend_dir / ".env.example"
    env_file = backend_dir / ".env"
    if env_example.exists() and not env_file.exists():
        print("Creating .env file from example...")
        with open(env_example) as f:
            content = f.read()
        with open(env_file, 'w') as f:
            f.write(content)
    
    print("✅ Backend setup complete!")
    return True

def setup_frontend():
    """Set up the frontend environment"""
    print("\n🔧 Setting up frontend...")
    
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        return False
    
    # Install dependencies
    print("Installing Node.js dependencies...")
    if not run_command("npm install", cwd=frontend_dir):
        print("❌ Failed to install Node.js dependencies")
        return False
    
    # Copy environment file
    env_example = frontend_dir / ".env.example"
    env_file = frontend_dir / ".env"
    if env_example.exists() and not env_file.exists():
        print("Creating .env file from example...")
        with open(env_example) as f:
            content = f.read()
        with open(env_file, 'w') as f:
            f.write(content)
    
    print("✅ Frontend setup complete!")
    return True

def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    
    directories = [
        "backend/config",
        "backend/logs",
        "backend/uploads",
        "docs/images"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created {directory}")

def main():
    """Main setup function"""
    print("🚀 Document Embedding Platform Setup")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("backend").exists() or not Path("frontend").exists():
        print("❌ Please run this script from the project root directory")
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Setup backend
    if not setup_backend():
        print("❌ Backend setup failed")
        sys.exit(1)
    
    # Setup frontend
    if not setup_frontend():
        print("❌ Frontend setup failed")
        sys.exit(1)
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Configure your embedder and vector database in backend/.env")
    print("2. Start the backend: cd backend && python -m uvicorn app.main:app --reload")
    print("3. Start the frontend: cd frontend && npm start")
    print("4. Open http://localhost:3000 in your browser")
    
if __name__ == "__main__":
    main() 