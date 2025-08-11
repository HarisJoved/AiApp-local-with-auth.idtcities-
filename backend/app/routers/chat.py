"""
FastAPI router for chat functionality with RAG support.
"""

import asyncio
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
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
    ChatMessageRequest,
    TopicListResponse,
    TopicInfo,
    TopicCreateRequest,
    SessionCreateUnderTopicRequest,
    MessageRecord,
    SessionMessagesResponse,
)
from app.models.config import ChatModelConfig
from app.services.hybrid_rag_service import HybridRAGService
from app.core.chat_models.base import ChatMessage
from app.routers.auth import router as _auth_router  # ensure module import doesn't break
from app.core.session.session_manager import SessionManager, FileSessionStorage, InMemorySessionStorage
from app.config.settings import config_manager, settings
from app.services.mongo_chat_store import get_mongo_store
from app.auth.deps import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])

# Global Hybrid RAG service instance
hybrid_rag_service: Optional[HybridRAGService] = None
chat_graph_service = None


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


def get_chat_graph():
    return None


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    rag_service: HybridRAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
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
        
        # Bind request to authenticated user if not provided
        request.user_id = request.user_id or current_user.get("user_id")

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
        
        # Ensure user/topic/session via MongoDB if user_id provided
        session_id = request.session_id
        store = get_mongo_store()
        if request.user_id:
            topic_id = request.topic_id
            if not topic_id:
                inferred = (request.message or "New Chat").strip().split("\n")[0][:60]
                # Reuse last topic if exists, else create once
                topic_id = await store.get_or_create_default_topic(request.user_id, inferred)
            if not session_id:
                session_id = await store.create_session(request.user_id, topic_id, title="New Chat")
        else:
            # Fallback to in-memory/file session manager
            if not session_id:
                new_session = await rag_service.create_session(request.user_id)
                session_id = new_session.session_id
        
        # Prepare previous chat history from MongoDB (if available)
        prior_messages: Optional[List[Any]] = None
        if request.user_id and session_id:
            # Pull more history to ensure multi-turn sessions are preserved
            history = await store.get_last_messages(session_id, limit=max(settings.chat_history_limit, 50))
            # Convert to LangChain-compatible messages
            from langchain.schema import HumanMessage, AIMessage
            prior_messages = []
            for m in history:
                if m.get("role") == "user":
                    prior_messages.append(HumanMessage(content=m.get("content", "")))
                elif m.get("role") == "assistant":
                    prior_messages.append(AIMessage(content=m.get("content", "")))

        # Process chat request with Hybrid RAG service, injecting history when available
        result = await rag_service.chat(
            message=request.message,
            session_id=session_id,
            user_id=request.user_id,
            use_rag=request.use_rag,
            chat_history_override=prior_messages,
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
        
        response_obj = ChatResponse(
            message=result.message,
            session_id=result.session_id,
            model_info=result.model_info,
            usage=result.usage,
            retrieved_chunks=retrieved_chunks,
            retrieval_time=result.retrieval_time,
            generation_time=result.generation_time,
            total_time=result.total_time
        )

        # Store messages as a pair in MongoDB
        if request.user_id and session_id:
            try:
                await store.add_message_pair(session_id, user_content=request.message, assistant_content=result.message)
                # Ensure the session has a meaningful title
                inferred = (request.message or "New Chat").strip().split("\n")[0][:60]
                await store.update_session_title_if_default(session_id, inferred)
            except Exception as e:
                print(f"⚠️ Failed to write messages to MongoDB: {e}")

        return response_obj
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def stream_chat_response(rag_service: HybridRAGService, request: ChatRequest, kwargs: Dict[str, Any]):
    """Stream chat response"""
    try:
        # Ensure user/topic/session via MongoDB if provided
        session_id = request.session_id
        store = get_mongo_store()
        if request.user_id:
            topic_id = request.topic_id
            if not topic_id:
                inferred = (request.message or "New Chat").strip().split("\n")[0][:60]
                topic_id = await store.get_or_create_default_topic(request.user_id, inferred)
            if not session_id:
                session_id = await store.create_session(request.user_id, topic_id, title="New Chat")
        else:
            if not session_id:
                new_session = await rag_service.create_session(request.user_id)
                session_id = new_session.session_id
        
        # Stream the response with Hybrid RAG service
        # Prepare prior history
        prior_messages = None
        if request.user_id and session_id:
            from langchain.schema import HumanMessage, AIMessage
            history = await store.get_last_messages(session_id, limit=max(settings.chat_history_limit, 50))
            prior_messages = []
            for m in history:
                if m.get("role") == "user":
                    prior_messages.append(HumanMessage(content=m.get("content", "")))
                elif m.get("role") == "assistant":
                    prior_messages.append(AIMessage(content=m.get("content", "")))

        async for chunk in rag_service.stream_chat(
            message=request.message,
            session_id=session_id,
            user_id=request.user_id,
            use_rag=request.use_rag,
            chat_history_override=prior_messages,
            **kwargs
        ):
            yield f"data: {chunk}\n\n"
        
        # Send end marker
        yield "data: [DONE]\n\n"
    
    except Exception as e:
        yield f"data: Error: {str(e)}\n\n"


@router.get("/topics", response_model=TopicListResponse)
async def list_topics(user_id: str = Query(...), current_user: dict = Depends(get_current_user)):
    if user_id != current_user.get("user_id"):
        raise HTTPException(status_code=403, detail="Forbidden")
    store = get_mongo_store()
    topics = await store.list_topics(user_id)
    topic_infos = [TopicInfo(**t) for t in topics]
    return TopicListResponse(topics=topic_infos, total=len(topic_infos))


@router.post("/topics", response_model=TopicInfo)
async def create_topic(request: TopicCreateRequest, current_user: dict = Depends(get_current_user)):
    if request.user_id != current_user.get("user_id"):
        raise HTTPException(status_code=403, detail="Forbidden")
    store = get_mongo_store()
    topic_id = await store.create_topic(request.user_id, request.title)
    return TopicInfo(topic_id=topic_id, title=request.title, created_at=datetime.utcnow().isoformat(), session_count=0)


@router.get("/topics/{topic_id}/sessions", response_model=SessionListResponse)
async def list_sessions_under_topic(topic_id: str, user_id: str = Query(...), current_user: dict = Depends(get_current_user)):
    if user_id != current_user.get("user_id"):
        raise HTTPException(status_code=403, detail="Forbidden")
    store = get_mongo_store()
    sessions = await store.list_sessions(user_id=user_id, topic_id=topic_id)
    session_infos = [
        SessionInfo(
            session_id=s["session_id"],
            user_id=user_id,
            title=s["title"],
            created_at=s["created_at"],
            last_activity=s["last_activity"],
            message_count=s.get("message_count", 0),
        )
        for s in sessions
    ]
    return SessionListResponse(sessions=session_infos, total=len(session_infos))


@router.post("/topics/{topic_id}/sessions", response_model=SessionInfo)
async def create_session_under_topic(topic_id: str, request: SessionCreateUnderTopicRequest, current_user: dict = Depends(get_current_user)):
    if request.user_id != current_user.get("user_id"):
        raise HTTPException(status_code=403, detail="Forbidden")
    store = get_mongo_store()
    session_id = await store.create_session(user_id=request.user_id, topic_id=topic_id, title=request.title or "New Chat")
    now = datetime.utcnow().isoformat()
    return SessionInfo(session_id=session_id, user_id=request.user_id, title=request.title or "New Chat", created_at=now, last_activity=now, message_count=0)


@router.get("/sessions/{session_id}/messages", response_model=SessionMessagesResponse)
async def get_session_messages(session_id: str, current_user: dict = Depends(get_current_user)):
    store = get_mongo_store()
    # Ensure the session belongs to current_user
    sessions = await store.list_sessions(user_id=current_user.get("user_id"))
    if session_id not in [s["session_id"] for s in sessions]:
        raise HTTPException(status_code=403, detail="Forbidden")
    msgs = await store.get_last_messages(session_id=session_id, limit=100)
    records = [MessageRecord(**m) for m in msgs]
    return SessionMessagesResponse(session_id=session_id, messages=records)


@router.post("/sessions", response_model=SessionInfo)
async def create_session(
    request: SessionCreateRequest,
    rag_service: HybridRAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
):
    """Create a new chat session"""
    try:
        store = get_mongo_store()
        if request.user_id and request.user_id != current_user.get("user_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
        if request.user_id:
            topic_id = await store.create_topic(request.user_id, title="General")
            session_id = await store.create_session(request.user_id, topic_id, title=request.title or "New Chat")
            now = datetime.utcnow().isoformat()
            return SessionInfo(
                session_id=session_id,
                user_id=request.user_id,
                title=request.title or "New Chat",
                created_at=now,
                last_activity=now,
                message_count=0
            )
        else:
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
    rag_service: HybridRAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
):
    """List chat sessions"""
    try:
        store = get_mongo_store()
        if user_id:
            if user_id != current_user.get("user_id"):
                raise HTTPException(status_code=403, detail="Forbidden")
            sessions_data = await store.list_sessions(user_id=user_id)
            sessions = [
                SessionInfo(
                    session_id=s["session_id"],
                    user_id=user_id,
                    title=s.get("title", "New Chat"),
                    created_at=s.get("created_at", datetime.utcnow().isoformat()),
                    last_activity=s.get("last_activity", datetime.utcnow().isoformat()),
                    message_count=s.get("message_count", 0),
                )
                for s in sessions_data
            ]
            return SessionListResponse(sessions=sessions, total=len(sessions))
        else:
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
    rag_service: HybridRAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
):
    """Get chat session history from MongoDB if available, otherwise from in-memory sessions."""
    try:
        store = get_mongo_store()
        # Access control: ensure session belongs to user
        user_sessions = await store.list_sessions(user_id=current_user.get("user_id"))
        if session_id not in [s["session_id"] for s in user_sessions]:
            raise HTTPException(status_code=403, detail="Forbidden")
        msgs = await store.get_last_messages(session_id=session_id, limit=100)
        if msgs:
            messages = [ChatMessageRequest(role=m["role"], content=m["content"]) for m in msgs]
            now = datetime.utcnow().isoformat()
            return SessionHistoryResponse(
                session_id=session_id,
                messages=messages,
                title="Chat",
                created_at=now,
                last_activity=now,
            )
        # Fallback: in-memory/file session
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
    rag_service: HybridRAGService = Depends(get_rag_service),
    current_user: dict = Depends(get_current_user)
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