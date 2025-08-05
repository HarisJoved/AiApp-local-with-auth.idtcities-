#!/usr/bin/env python3
"""
Install the new langchain-huggingface dependency and test LangChain initialization.
"""

import subprocess
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))


def install_dependency():
    """Install the langchain-huggingface package"""
    print("📦 Installing langchain-huggingface...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "langchain-huggingface>=0.0.1"
        ], check=True)
        print("✅ langchain-huggingface installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install langchain-huggingface: {e}")
        return False


async def test_langchain_import():
    """Test if the new import works"""
    print("🧪 Testing LangChain imports...")
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        print("✅ HuggingFaceEmbeddings import successful!")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


async def test_langchain_service():
    """Test LangChain service initialization"""
    print("🚀 Testing LangChain RAG service initialization...")
    try:
        from app.services.langchain_rag_service import LangChainRAGService
        from app.core.session.session_manager import SessionManager
        from app.models.config import AppConfig
        
        # Create a minimal test config
        config = AppConfig()
        session_manager = SessionManager(config)
        
        # Test service creation
        service = LangChainRAGService(config, session_manager)
        print("✅ LangChain RAG service created successfully!")
        return True
    except Exception as e:
        print(f"❌ Service creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    print("🔧 LangChain Fix Installation & Test")
    print("====================================")
    
    # Install dependency
    if not install_dependency():
        return
    
    # Import test
    import asyncio
    
    async def run_tests():
        import_ok = await test_langchain_import()
        if not import_ok:
            return
            
        service_ok = await test_langchain_service()
        
        print("\n📊 Results:")
        print("===========")
        if import_ok and service_ok:
            print("🎉 SUCCESS! LangChain fixes are working!")
            print("You can now restart your backend server.")
        else:
            print("❌ Some tests failed. Check the errors above.")
    
    asyncio.run(run_tests())


if __name__ == "__main__":
    main()