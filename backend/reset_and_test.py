#!/usr/bin/env python3
"""
Reset the RAG service and test if LangChain works now.
"""

import asyncio
import requests
import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))


async def reset_and_test():
    """Reset the service and test if it works"""
    print("🔄 Resetting RAG service...")
    
    try:
        # Reset the service
        response = requests.post("http://localhost:8000/chat/reset")
        if response.status_code == 200:
            print("✅ Service reset successfully")
        else:
            print(f"⚠️ Service reset failed: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Could not reset service: {e}")
    
    # Wait a moment
    await asyncio.sleep(2)
    
    # Check health
    try:
        print("🏥 Checking service health...")
        response = requests.get("http://localhost:8000/chat/health")
        if response.status_code == 200:
            health = response.json()
            print(f"Status: {health.get('status')}")
            print(f"Missing components: {health.get('missing_components', [])}")
            print(f"Chat model: {health.get('chat_model')}")
            print(f"Embedder: {health.get('embedder')}")
            print(f"Vector DB: {health.get('vector_db')}")
            
            if health.get('status') == 'ready':
                print("🎉 Service is ready!")
                return True
            else:
                print("❌ Service not ready")
                return False
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


async def test_debug_endpoint():
    """Test the debug endpoint"""
    try:
        print("\n🔍 Checking debug info...")
        response = requests.get("http://localhost:8000/chat/debug")
        if response.status_code == 200:
            debug = response.json()
            print(f"Config: {debug.get('config', {})}")
            print(f"Service: {debug.get('service', {})}")
            
            service_info = debug.get('service', {})
            if service_info.get('service_type') == 'langchain':
                print("🔵 ✅ LangChain is active!")
                return True
            elif service_info.get('service_type') == 'custom':
                print("🟡 Custom RAG is active (LangChain failed)")
                return False
            else:
                print("❌ No active service")
                return False
        else:
            print(f"❌ Debug endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Debug endpoint error: {e}")
        return False


async def main():
    """Main function"""
    print("🚀 Testing LangChain RAG Fix")
    print("============================")
    
    # Test if server is running
    try:
        requests.get("http://localhost:8000/", timeout=2)
    except:
        print("❌ Backend server is not running!")
        print("Please start it with: python start_backend.py")
        return
    
    # Reset and test
    service_ready = await reset_and_test()
    langchain_active = await test_debug_endpoint()
    
    print("\n📊 Results:")
    print("===========")
    if service_ready and langchain_active:
        print("🎉 SUCCESS! LangChain RAG is working!")
        print("The attribute name fix resolved the issue.")
    elif service_ready and not langchain_active:
        print("⚠️ Service is ready but using Custom RAG fallback.")
        print("LangChain still has initialization issues.")
    else:
        print("❌ Service is not ready.")
        print("Check the backend logs for errors.")


if __name__ == "__main__":
    asyncio.run(main())