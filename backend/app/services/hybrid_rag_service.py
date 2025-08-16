"""
Hybrid RAG service that falls back from LangChain to custom implementation
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.models.config import AppConfig
from app.core.session.session_manager import SessionManager, ChatSession
from app.core.chat_models.base import ChatMessage

# Try to import LangChain service first
try:
    from app.services.langchain_rag_service import LangChainRAGService, ChatResult
    LANGCHAIN_AVAILABLE = True
    print("✅ LangChain RAG service available")
except Exception as e:
    print(f"⚠️ LangChain RAG service not available: {e}")
    LANGCHAIN_AVAILABLE = False

# Import the original working RAG service as fallback
try:
    from app.services.rag_service import RAGService
    CUSTOM_RAG_AVAILABLE = True
    print("✅ Custom RAG service available")
except Exception as e:
    print(f"❌ Custom RAG service not available: {e}")
    CUSTOM_RAG_AVAILABLE = False


class HybridRAGService:
    """
    Hybrid RAG service that tries LangChain first, falls back to custom implementation
    """
    
    def __init__(self, config: AppConfig, session_manager: SessionManager):
        self.config = config
        self.session_manager = session_manager
        self.active_service = None
        self.service_type = None
        
    async def initialize(self) -> bool:
        """Initialize the RAG service, trying LangChain first, then custom"""
        
        # Try LangChain first
        if LANGCHAIN_AVAILABLE:
            try:
                print("🔵 Attempting LangChain RAG initialization...")
                langchain_service = LangChainRAGService(self.config, self.session_manager)
                success = await langchain_service.initialize()
                
                if success:
                    is_ready, missing = langchain_service.is_ready()
                    if is_ready:
                        print("✅ LangChain RAG service initialized successfully!")
                        self.active_service = langchain_service
                        self.service_type = "langchain"
                        return True
                    else:
                        print(f"⚠️ LangChain service not ready, missing: {missing}")
                else:
                    print("⚠️ LangChain initialization failed")
                    
            except Exception as e:
                print(f"⚠️ LangChain initialization error: {e}")
        
        # Fall back to custom RAG service
        if CUSTOM_RAG_AVAILABLE:
            try:
                print("🟡 Falling back to custom RAG service...")
                from app.services.factory import service_factory
                
                # Initialize services using the original factory
                embedder, vector_db, chat_model = await service_factory.initialize_all_services(self.config)
                
                if embedder and vector_db and chat_model:
                    custom_service = RAGService(
                        embedder=embedder,
                        vector_db=vector_db,
                        chat_model=chat_model,
                        session_manager=self.session_manager
                    )
                    
                    # Update RAG configuration
                    rag_config = {
                        "top_k": self.config.rag_top_k,
                        "similarity_threshold": self.config.rag_similarity_threshold,
                        "max_context_length": self.config.rag_max_context_length
                    }
                    custom_service.update_retrieval_config(rag_config)
                    
                    print("✅ Custom RAG service initialized successfully!")
                    self.active_service = custom_service
                    self.service_type = "custom"
                    return True
                else:
                    print("❌ Custom RAG service missing components")
                    
            except Exception as e:
                print(f"❌ Custom RAG initialization error: {e}")
                import traceback
                traceback.print_exc()
        
        print("❌ Both LangChain and custom RAG initialization failed")
        return False
    
    def is_ready(self) -> Tuple[bool, List[str]]:
        """Check if the active service is ready"""
        if not self.active_service:
            return False, ["no_active_service"]
        
        return self.active_service.is_ready()
    
    async def chat(self, message: str, session_id: str, user_id: Optional[str] = None, use_rag: bool = True, **kwargs) -> Any:
        """Chat using the active service"""
        if not self.active_service:
            raise ValueError("No active RAG service available")
        
        if self.service_type == "langchain":
            # LangChain service returns ChatResult
            return await self.active_service.chat(message, session_id, user_id, use_rag, **kwargs)
        else:
            # Custom service returns RAGResult, need to adapt
            # Remove langchain-only kwargs to avoid unexpected-kwargs errors
            kwargs.pop("chat_history_override", None)
            result = await self.active_service.chat(message, session_id, user_id, use_rag, **kwargs)
            
            # Convert RAGResult to ChatResult format for compatibility
            class ChatResult:
                def __init__(self, rag_result):
                    self.message = rag_result.response.message
                    self.session_id = rag_result.session.session_id
                    self.model_info = rag_result.response.model_info
                    self.usage = rag_result.response.usage
                    self.retrieved_chunks = rag_result.retrieved_chunks
                    self.retrieval_time = rag_result.retrieval_time
                    self.generation_time = rag_result.generation_time
                    self.total_time = rag_result.total_time
                    self.debug = None
            
            return ChatResult(result)
    
    async def stream_chat(self, message: str, session_id: str, user_id: Optional[str] = None, use_rag: bool = True, **kwargs):
        """Stream chat using the active service"""
        if not self.active_service:
            raise ValueError("No active RAG service available")
        
        if self.service_type != "langchain":
            kwargs.pop("chat_history_override", None)
        async for chunk in self.active_service.stream_chat(message, session_id, user_id, use_rag, **kwargs):
            yield chunk
    
    # Delegate all other methods to the active service
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        if not self.active_service:
            return None
        return await self.active_service.get_session(session_id)
    
    async def list_sessions(self, user_id: Optional[str] = None) -> List[ChatSession]:
        if not self.active_service:
            return []
        return await self.active_service.list_sessions(user_id)
    
    async def delete_session(self, session_id: str) -> bool:
        if not self.active_service:
            return False
        return await self.active_service.delete_session(session_id)
    
    async def create_session(self, user_id: Optional[str] = None, title: Optional[str] = None) -> ChatSession:
        if not self.active_service:
            raise ValueError("No active RAG service available")
        return await self.active_service.create_session(user_id, title)
    
    def update_retrieval_config(self, config: Dict[str, Any]) -> None:
        if self.active_service:
            self.active_service.update_retrieval_config(config)
            
    def _get_model_info(self) -> str:
        """Get model info from active service"""
        if not self.active_service:
            return "No active service"
        
        if self.service_type == "langchain" and hasattr(self.active_service, '_get_model_info'):
            return self.active_service._get_model_info()
        elif hasattr(self.active_service, 'chat_model') and hasattr(self.active_service.chat_model, 'get_model_info'):
            return self.active_service.chat_model.get_model_info()
        else:
            return f"{self.service_type} service"
    
    # Properties for compatibility
    @property
    def embeddings(self):
        if self.service_type == "langchain":
            return getattr(self.active_service, 'embeddings', None)
        elif hasattr(self.active_service, 'embedder'):
            return self.active_service.embedder
        return None
    
    @property
    def vectorstore(self):
        if self.service_type == "langchain":
            return getattr(self.active_service, 'vectorstore', None)
        elif hasattr(self.active_service, 'vector_db'):
            return self.active_service.vector_db
        return None
    
    @property
    def chat_model(self):
        if self.service_type == "langchain":
            return getattr(self.active_service, 'chat_model', None)
        elif hasattr(self.active_service, 'chat_model'):
            return self.active_service.chat_model
        return None