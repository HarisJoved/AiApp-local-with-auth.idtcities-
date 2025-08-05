#!/usr/bin/env python3
"""
Test script to verify Hybrid RAG service works correctly.
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.config.settings import config_manager
from app.services.hybrid_rag_service import HybridRAGService
from app.core.session.session_manager import SessionManager, InMemorySessionStorage


async def test_hybrid_rag():
    """Test Hybrid RAG service initialization and functionality"""
    print("🧪 Testing Hybrid RAG Service...")
    
    try:
        # Get current configuration
        print("  Getting configuration...")
        current_config = config_manager.get_current_config()
        if not current_config:
            print("  ❌ No configuration found. Please configure services first.")
            return False
        
        print(f"  ✅ Found configuration with embedder: {current_config.embedder.type}")
        print(f"      Vector DB: {current_config.vector_db.type}")
        if current_config.chat_model:
            print(f"      Chat model: {current_config.chat_model.type}")
        else:
            print("      Chat model: Not configured")
        
        # Create session manager
        print("  Creating session manager...")
        session_storage = InMemorySessionStorage()
        session_manager = SessionManager(session_storage)
        await session_manager.start_cleanup_task()
        print("  ✅ Session manager created")
        
        # Initialize Hybrid RAG service
        print("  Creating Hybrid RAG service...")
        rag_service = HybridRAGService(current_config, session_manager)
        
        print("  Initializing Hybrid components...")
        success = await rag_service.initialize()
        if not success:
            print("  ❌ Failed to initialize Hybrid RAG service")
            return False
        
        print(f"  ✅ Hybrid RAG service initialized successfully! Service type: {rag_service.service_type}")
        
        # Test service readiness
        print("  Testing service readiness...")
        is_ready, missing = rag_service.is_ready()
        if not is_ready:
            print(f"  ⚠️ Service not ready. Missing: {', '.join(missing)}")
        else:
            print("  ✅ Service is ready")
        
        # Test creating a session
        print("  Testing session creation...")
        session = await rag_service.create_session("test_user", "Test Hybrid Session")
        print(f"  ✅ Session created: {session.session_id}")
        
        # Test simple chat without RAG
        print("  Testing simple chat without RAG...")
        try:
            result = await rag_service.chat(
                message="Hello! This is a test message for Hybrid RAG.",
                session_id=session.session_id,
                user_id="test_user",
                use_rag=False
            )
            print(f"  ✅ Chat successful: {result.message[:50]}...")
            print(f"      Service type used: {rag_service.service_type}")
            print(f"      Generation time: {result.generation_time:.2f}s")
        except Exception as e:
            print(f"  ❌ Chat failed: {e}")
            traceback.print_exc()
            return False
        
        # Test RAG-enabled chat (if documents are available)
        print("  Testing RAG-enabled chat...")
        try:
            result = await rag_service.chat(
                message="What information do you have available?",
                session_id=session.session_id,
                user_id="test_user",
                use_rag=True
            )
            print(f"  ✅ RAG chat successful: {result.message[:50]}...")
            print(f"      Retrieved chunks: {len(result.retrieved_chunks)}")
            print(f"      Retrieval time: {result.retrieval_time:.2f}s")
            print(f"      Generation time: {result.generation_time:.2f}s")
            print(f"      Total time: {result.total_time:.2f}s")
        except Exception as e:
            print(f"  ❌ RAG chat failed: {e}")
            traceback.print_exc()
            return False
        
        print("  🎉 Hybrid RAG service test completed successfully!")
        return True
        
    except Exception as e:
        print(f"  ❌ Hybrid RAG service test failed: {e}")
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("🚀 Hybrid RAG Service Test")
    print("===========================")
    
    success = await test_hybrid_rag()
    
    print("\n📊 Test Results:")
    print("================")
    if success:
        print("✅ Hybrid RAG service is working correctly!")
        print("\nThe service will automatically choose the best RAG implementation:")
        print("- 🔵 LangChain RAG (preferred, professional implementation)")
        print("- 🟡 Custom RAG (fallback, your original working implementation)")
        print("\nThis ensures your system always works, even if LangChain has issues.")
    else:
        print("❌ Hybrid RAG service has issues.")
        print("\nTroubleshooting:")
        print("1. Check that your original configuration was working")
        print("2. Verify all services are properly configured")
        print("3. Check API keys and credentials")
        print("4. Run: python start_backend.py")


if __name__ == "__main__":
    asyncio.run(main())