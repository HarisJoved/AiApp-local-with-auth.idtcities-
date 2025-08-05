#!/usr/bin/env python3
"""
Test script to debug RAG service issues.
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.config.settings import config_manager
from app.services.factory import service_factory
from app.services.rag_service import RAGService
from app.core.session.session_manager import SessionManager, InMemorySessionStorage


async def test_rag_service():
    """Test RAG service initialization and basic functionality"""
    print("🧪 Testing RAG Service...")
    
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
        
        # Initialize services
        print("  Initializing services...")
        embedder, vector_db, chat_model = await service_factory.initialize_all_services(current_config)
        
        if not embedder:
            print("  ❌ Failed to initialize embedder")
            return False
        print(f"  ✅ Embedder initialized: {type(embedder).__name__}")
        
        if not vector_db:
            print("  ❌ Failed to initialize vector database")
            return False
        print(f"  ✅ Vector DB initialized: {type(vector_db).__name__}")
        
        if not chat_model:
            print("  ❌ Failed to initialize chat model")
            return False
        print(f"  ✅ Chat model initialized: {type(chat_model).__name__}")
        
        # Create session manager
        print("  Creating session manager...")
        session_storage = InMemorySessionStorage()
        session_manager = SessionManager(session_storage)
        await session_manager.start_cleanup_task()
        print("  ✅ Session manager created")
        
        # Initialize RAG service
        print("  Creating RAG service...")
        rag_service = RAGService(
            embedder=embedder,
            vector_db=vector_db,
            chat_model=chat_model,
            session_manager=session_manager
        )
        
        # Update RAG configuration
        rag_config = {
            "top_k": current_config.rag_top_k,
            "similarity_threshold": current_config.rag_similarity_threshold,
            "max_context_length": current_config.rag_max_context_length
        }
        rag_service.update_retrieval_config(rag_config)
        print("  ✅ RAG service created and configured")
        
        # Test RAG service readiness
        print("  Testing RAG service readiness...")
        is_ready, missing = rag_service.is_ready()
        if not is_ready:
            print(f"  ⚠️ RAG service not ready. Missing: {', '.join(missing)}")
        else:
            print("  ✅ RAG service is ready")
        
        # Test creating a session
        print("  Testing session creation...")
        session = await rag_service.create_session("test_user", "Test Session")
        print(f"  ✅ Session created: {session.session_id}")
        
        # Test simple chat (without RAG first)
        print("  Testing simple chat without RAG...")
        try:
            result = await rag_service.chat(
                message="Hello, this is a test message",
                session_id=session.session_id,
                user_id="test_user",
                use_rag=False
            )
            print(f"  ✅ Chat successful: {result.response.message[:50]}...")
            print(f"      Generation time: {result.generation_time:.2f}s")
        except Exception as e:
            print(f"  ❌ Chat failed: {e}")
            traceback.print_exc()
            return False
        
        # Test RAG-enabled chat (if documents are available)
        print("  Testing RAG-enabled chat...")
        try:
            result = await rag_service.chat(
                message="What documents do you have?",
                session_id=session.session_id,
                user_id="test_user",
                use_rag=True
            )
            print(f"  ✅ RAG chat successful: {result.response.message[:50]}...")
            print(f"      Retrieved chunks: {len(result.retrieved_chunks)}")
            print(f"      Retrieval time: {result.retrieval_time:.2f}s")
            print(f"      Generation time: {result.generation_time:.2f}s")
        except Exception as e:
            print(f"  ❌ RAG chat failed: {e}")
            traceback.print_exc()
            return False
        
        print("  🎉 RAG service test completed successfully!")
        return True
        
    except Exception as e:
        print(f"  ❌ RAG service test failed: {e}")
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("🔧 RAG Service Debug Test")
    print("=========================")
    
    success = await test_rag_service()
    
    print("\n📊 Test Results:")
    print("================")
    if success:
        print("✅ RAG service is working correctly!")
        print("\nThe issue might be in the FastAPI endpoint or frontend.")
        print("Check the backend server logs for more details.")
    else:
        print("❌ RAG service has issues.")
        print("\nCommon solutions:")
        print("1. Make sure all services are configured")
        print("2. Check API keys and credentials")
        print("3. Verify vector database connectivity")
        print("4. Check chat model configuration")


if __name__ == "__main__":
    asyncio.run(main())