#!/usr/bin/env python3
"""
Test script to verify LangChain RAG service works correctly.
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.config.settings import config_manager
from app.services.langchain_rag_service import LangChainRAGService
from app.core.session.session_manager import SessionManager, InMemorySessionStorage


async def test_langchain_rag():
    """Test LangChain RAG service initialization and functionality"""
    print("🧪 Testing LangChain RAG Service...")
    
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
        
        # Initialize LangChain RAG service
        print("  Creating LangChain RAG service...")
        rag_service = LangChainRAGService(current_config, session_manager)
        
        print("  Initializing LangChain components...")
        success = await rag_service.initialize()
        if not success:
            print("  ❌ Failed to initialize LangChain RAG service")
            return False
        
        print("  ✅ LangChain RAG service initialized successfully")
        
        # Test service readiness
        print("  Testing service readiness...")
        is_ready, missing = rag_service.is_ready()
        if not is_ready:
            print(f"  ⚠️ Service not ready. Missing: {', '.join(missing)}")
        else:
            print("  ✅ Service is ready")
        
        # Test creating a session
        print("  Testing session creation...")
        session = await rag_service.create_session("test_user", "Test LangChain Session")
        print(f"  ✅ Session created: {session.session_id}")
        
        # Test simple chat without RAG
        print("  Testing simple chat without RAG...")
        try:
            result = await rag_service.chat(
                message="Hello! This is a test message for LangChain.",
                session_id=session.session_id,
                user_id="test_user",
                use_rag=False
            )
            print(f"  ✅ Chat successful: {result.message[:50]}...")
            print(f"      Model: {result.model_info}")
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
        
        print("  🎉 LangChain RAG service test completed successfully!")
        return True
        
    except Exception as e:
        print(f"  ❌ LangChain RAG service test failed: {e}")
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("🚀 LangChain RAG Service Test")
    print("=============================")
    
    success = await test_langchain_rag()
    
    print("\n📊 Test Results:")
    print("================")
    if success:
        print("✅ LangChain RAG service is working correctly!")
        print("\nYou can now use the chat endpoints with improved LangChain RAG.")
        print("Benefits of LangChain implementation:")
        print("- Better conversation memory management")
        print("- More robust error handling")
        print("- Native vectorstore integration")
        print("- Improved streaming support")
        print("- Professional RAG pipeline")
    else:
        print("❌ LangChain RAG service has issues.")
        print("\nCommon solutions:")
        print("1. Install LangChain dependencies: pip install -r requirements.txt")
        print("2. Make sure all services are configured")
        print("3. Check API keys and credentials")
        print("4. Verify vector database connectivity")
        print("5. Check chat model configuration")


if __name__ == "__main__":
    asyncio.run(main())