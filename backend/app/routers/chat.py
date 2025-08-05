"""
FastAPI router for chat functionality with RAG support.
"""

import asyncio
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from datetime import datetime

from app.models.chat import (
    ChatRequest, 
    ChatResponse, 
    RetrievedChunk,
    SessionInfo, 
    SessionListResponse, 
    SessionCreateRequest,
    SessionHistoryResponse,
    ChatMessageRequest
)
from app.models.config import ChatModelConfig
from app.services.hybrid_rag_service import HybridRAGService
from app.core.chat_models.base import ChatMessage
from app.core.session.session_manager import SessionManager, FileSessionStorage, InMemorySessionStorage
from app.config.settings import config_manager

router = APIRouter(prefix="/chat", tags=["chat"])

# Global Hybrid RAG service instance
hybrid_rag_service: Optional[HybridRAGService] = None


def reset_rag_service():
    """Reset the global RAG service instance"""
    global hybrid_rag_service
    hybrid_rag_service = None
    print("RAG service instance reset")


async def get_rag_service() -> HybridRAGService:
    """Get or initialize Hybrid RAG service"""
    global hybrid_rag_service
    
    # Always get fresh configuration
    current_config = config_manager.get_current_config()
    if not current_config:
        raise HTTPException(status_code=503, detail="Services not configured. Please configure embedder, vector DB, and chat model first.")
    
    # Check if we need to reinitialize (config changed or service not ready)
    needs_init = (
        not hybrid_rag_service or 
        not hybrid_rag_service.is_ready()[0]
    )
    
    if needs_init:
        print("🚀 Initializing Hybrid RAG service...")
        
        # Create session manager based on config
        if hasattr(current_config, 'session_storage_type') and current_config.session_storage_type == "file":
            session_storage = FileSessionStorage(current_config.session_storage_path)
        else:
            session_storage = InMemorySessionStorage()
        
        session_manager = SessionManager(session_storage)
        await session_manager.start_cleanup_task()
        
        # Initialize Hybrid RAG service (tries LangChain first, falls back to custom)
        hybrid_rag_service = HybridRAGService(current_config, session_manager)
        
        # Initialize with fallback capability
        try:
            success = await hybrid_rag_service.initialize()
            if not success:
                is_ready, missing = hybrid_rag_service.is_ready()
                raise HTTPException(
                    status_code=503, 
                    detail=f"Failed to initialize RAG service. Missing components: {', '.join(missing)}"
                )
            print("✅ Hybrid RAG service initialized successfully!")
        except Exception as e:
            print(f"❌ Error initializing Hybrid RAG service: {e}")
            hybrid_rag_service = None
            raise HTTPException(status_code=503, detail=f"Failed to initialize RAG service: {str(e)}")
    
    return hybrid_rag_service


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    rag_service: HybridRAGService = Depends(get_rag_service)
):
    """
    Chat with the AI assistant
    
    - **message**: User's message/question
    - **session_id**: Optional session ID (new session created if not provided)
    - **user_id**: Optional user ID for session management
    - **use_rag**: Whether to use document retrieval (default: true)
    - **stream**: Whether to stream the response (default: false)
    - **temperature**: Override model temperature
    - **max_tokens**: Override max tokens
    """
    try:
        # Check if RAG service is ready
        is_ready, missing = rag_service.is_ready()
        if not is_ready:
            raise HTTPException(
                status_code=503, 
                detail=f"Chat service not ready. Missing: {', '.join(missing)}"
            )
        
        # Prepare kwargs for model
        kwargs = {}
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens
        
        # Handle streaming response
        if request.stream:
            if not rag_service.chat_model.supports_streaming():
                raise HTTPException(status_code=400, detail="Current chat model does not support streaming")
            
            return StreamingResponse(
                stream_chat_response(rag_service, request, kwargs),
                media_type="text/plain"
            )
        
        # Generate session ID if not provided
        session_id = request.session_id
        if not session_id:
            new_session = await rag_service.create_session(request.user_id)
            session_id = new_session.session_id
        
        # Process chat request with Hybrid RAG service
        result = await rag_service.chat(
            message=request.message,
            session_id=session_id,
            user_id=request.user_id,
            use_rag=request.use_rag,
            **kwargs
        )
        
        # Convert retrieved chunks to response format
        retrieved_chunks = [
            RetrievedChunk(
                content=chunk.get("content", ""),
                score=chunk.get("score", 0.0),
                metadata=chunk.get("metadata", {})
            )
            for chunk in result.retrieved_chunks
        ]
        
        return ChatResponse(
            message=result.message,
            session_id=result.session_id,
            model_info=result.model_info,
            usage=result.usage,
            retrieved_chunks=retrieved_chunks,
            retrieval_time=result.retrieval_time,
            generation_time=result.generation_time,
            total_time=result.total_time
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def stream_chat_response(rag_service: HybridRAGService, request: ChatRequest, kwargs: Dict[str, Any]):
    """Stream chat response"""
    try:
        # Generate session ID if not provided
        session_id = request.session_id
        if not session_id:
            new_session = await rag_service.create_session(request.user_id)
            session_id = new_session.session_id
        
        # Stream the response with Hybrid RAG service
        async for chunk in rag_service.stream_chat(
            message=request.message,
            session_id=session_id,
            user_id=request.user_id,
            use_rag=request.use_rag,
            **kwargs
        ):
            yield f"data: {chunk}\n\n"
        
        # Send end marker
        yield "data: [DONE]\n\n"
    
    except Exception as e:
        yield f"data: Error: {str(e)}\n\n"


@router.post("/sessions", response_model=SessionInfo)
async def create_session(
    request: SessionCreateRequest,
    rag_service: HybridRAGService = Depends(get_rag_service)
):
    """Create a new chat session"""
    try:
        session = await rag_service.create_session(request.user_id, request.title)
        
        return SessionInfo(
            session_id=session.session_id,
            user_id=session.user_id,
            title=session.title,
            created_at=session.created_at.isoformat(),
            last_activity=session.last_activity.isoformat(),
            message_count=len(session.messages)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    user_id: Optional[str] = None,
    rag_service: HybridRAGService = Depends(get_rag_service)
):
    """List chat sessions"""
    try:
        sessions_data = await rag_service.list_sessions(user_id)
        
        sessions = [
            SessionInfo(
                session_id=session["session_id"],
                user_id=session.get("user_id"),
                title=session.get("title", "New Chat"),
                created_at=session.get("created_at", datetime.utcnow().isoformat()),
                last_activity=session.get("last_activity", datetime.utcnow().isoformat()),
                message_count=len(session.get("messages", []))
            )
            for session in sessions_data
        ]
        
        return SessionListResponse(
            sessions=sessions,
            total=len(sessions)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=SessionHistoryResponse)
async def get_session(
    session_id: str,
    rag_service: HybridRAGService = Depends(get_rag_service)
):
    """Get chat session history"""
    try:
        session = await rag_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        messages = [
            ChatMessageRequest(
                role=msg.role,
                content=msg.content
            )
            for msg in session.messages
        ]
        
        return SessionHistoryResponse(
            session_id=session.session_id,
            messages=messages,
            title=session.title,
            created_at=session.created_at.isoformat(),
            last_activity=session.last_activity.isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    rag_service: HybridRAGService = Depends(get_rag_service)
):
    """Delete a chat session"""
    try:
        await rag_service.delete_session(session_id)
        return {"message": "Session deleted successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def chat_health():
    """Check chat service health"""
    try:
        rag_service = await get_rag_service()
        is_ready, missing = rag_service.is_ready()
        
        # Get embedder info as string
        embedder_info = "Unknown"
        if rag_service.embeddings:
            if hasattr(rag_service.embeddings, 'model_name'):
                embedder_info = f"HuggingFace {rag_service.embeddings.model_name}"
            elif hasattr(rag_service.embeddings, 'model'):
                embedder_info = f"OpenAI {rag_service.embeddings.model}"
            else:
                embedder_info = "LangChain Embeddings"
        
        # Get chat model info
        chat_model_info = None
        if rag_service.chat_model:
            chat_model_info = rag_service._get_model_info()
        
        # Get vectorstore info
        vector_db_info = "not_configured"
        if rag_service.vectorstore:
            if hasattr(rag_service.vectorstore, '_collection_name'):
                vector_db_info = f"ChromaDB: {rag_service.vectorstore._collection_name}"
            elif hasattr(rag_service.vectorstore, '_index_name'):
                vector_db_info = f"Pinecone: {rag_service.vectorstore._index_name}"
            else:
                vector_db_info = "configured"
        
        return {
            "status": "ready" if is_ready else "not_ready",
            "missing_components": missing,
            "chat_model": chat_model_info,
            "embedder": embedder_info,
            "vector_db": vector_db_info
        }
    
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "missing_components": ["embeddings", "vectorstore", "chat_model", "retrieval_chain"],
            "chat_model": None,
            "embedder": "Unknown",
            "vector_db": "not_configured"
        }


@router.post("/reset")
async def reset_chat_service():
    """Reset the chat service (for debugging)"""
    reset_rag_service()
    return {"message": "Chat service reset successfully"}


@router.get("/debug")
async def debug_chat_service():
    """Debug endpoint to check service status"""
    try:
        current_config = config_manager.get_current_config()
        if not current_config:
            return {"error": "No configuration found"}
        
        config_info = {
            "embedder_configured": bool(current_config.embedder),
            "vector_db_configured": bool(current_config.vector_db),
            "chat_model_configured": bool(current_config.chat_model),
        }
        
        if current_config.embedder:
            config_info["embedder_type"] = str(current_config.embedder.type)
        if current_config.vector_db:  
            config_info["vector_db_type"] = str(current_config.vector_db.type)
        if current_config.chat_model:
            config_info["chat_model_type"] = str(current_config.chat_model.type)
        
        global hybrid_rag_service
        service_info = {
            "service_exists": hybrid_rag_service is not None,
            "service_ready": False,
            "missing_components": [],
            "service_type": "none"
        }
        
        if hybrid_rag_service:
            is_ready, missing = hybrid_rag_service.is_ready()
            service_info["service_ready"] = is_ready
            service_info["missing_components"] = missing
            service_info["service_type"] = getattr(hybrid_rag_service, 'service_type', 'unknown')
        
        return {
            "config": config_info,
            "service": service_info
        }
        
    except Exception as e:
        return {"error": str(e)}