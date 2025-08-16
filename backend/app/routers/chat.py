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
    ConversationInfo,
    ConversationListResponse,
    ConversationCreateRequest,
    ConversationHistoryResponse,
    ChatMessageRequest,
    RAGPromptCreate,
    RAGPromptUpdate,
    RAGPromptInfo,
    RAGPromptListResponse,
    RAGPromptActiveResponse,
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
    - conversation_id: Optional conversation ID (new conversation created if not provided)
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
        
        # Ensure conversation via MongoDB
        store = get_mongo_store()
        conversation_id = request.conversation_id
        if request.user_id:
            if not conversation_id:
                inferred = (request.message or "New Chat").strip().split("\n")[0][:60]
                conversation_id = await store.create_conversation(request.user_id, title=inferred, token_limit=request.token_limit or 128_000)
            else:
                convo = await store.get_conversation(conversation_id)
                if not convo or convo.get("user_id") != request.user_id:
                    raise HTTPException(status_code=403, detail="Forbidden")
        else:
            # Anonymous: generate a temporary conversation
            if not conversation_id:
                conversation_id = await store.create_conversation(user_id="anonymous", title="New Chat", token_limit=request.token_limit or 128_000)
        
        # Prepare chat history from summaries + recent messages and optional user-defined prompt
        prior_messages: Optional[List[Any]] = []
        try:
            from langchain.schema import HumanMessage, AIMessage, SystemMessage
            # Inject active user RAG prompt if available
            if request.user_id:
                active_prompt = await store.get_active_rag_prompt(request.user_id)
                if active_prompt and active_prompt.get("content"):
                    prior_messages.append(SystemMessage(content=str(active_prompt.get("content"))))
            summaries = await store.list_summaries(conversation_id)
            for s in summaries:
                layer = s.get("layer", 1)
                text = s.get("summary_text", "")
                prior_messages.append(SystemMessage(content=f"Conversation summary (layer {layer}): {text}"))
            history = await store.get_last_messages(conversation_id, limit=max(settings.chat_history_limit, 50))
            for m in history:
                if m.get("role") == "user":
                    prior_messages.append(HumanMessage(content=m.get("content", "")))
                elif m.get("role") == "assistant":
                    prior_messages.append(AIMessage(content=m.get("content", "")))
        except Exception as _:
            prior_messages = None

        # Process chat request with Hybrid RAG service, injecting history when available
        result = await rag_service.chat(
            message=request.message,
            session_id=conversation_id,  # use conversation id as memory key
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
        
        # Build debug info for UI
        debug_info: Dict[str, Any] = {}
        try:
            # System prompt from active user prompt
            if request.user_id:
                active_prompt = await store.get_active_rag_prompt(request.user_id)
                if active_prompt and active_prompt.get("content"):
                    debug_info["system_prompt"] = str(active_prompt.get("content"))
            # Base prompt from service
            if getattr(result, 'debug', None):
                if isinstance(result.debug, dict):
                    debug_info.update({k: v for k, v in result.debug.items() if k in ["base_prompt", "retriever_top_k", "used_chat_history"]})
            # Summaries used
            try:
                summaries = await store.list_summaries(conversation_id)
                debug_info["summaries"] = [s.get("summary_text", "") for s in summaries]
            except Exception:
                pass
            # Question and context
            debug_info["question"] = request.message
            debug_info["context"] = [
                {"content": rc.content, "score": rc.score, "metadata": rc.metadata}
                for rc in retrieved_chunks
            ]
            # Timings
            debug_info["timings"] = {
                "retrieval_time": getattr(result, 'retrieval_time', 0.0),
                "generation_time": getattr(result, 'generation_time', 0.0),
                "total_time": getattr(result, 'total_time', 0.0),
            }
        except Exception:
            pass

        response_obj = ChatResponse(
            message=result.message,
            conversation_id=conversation_id,
            model_info=result.model_info,
            usage=result.usage,
            retrieved_chunks=retrieved_chunks,
            retrieval_time=result.retrieval_time,
            generation_time=result.generation_time,
            total_time=result.total_time,
            debug=debug_info or None
        )

        # Store messages and run summarization if needed
        try:
            await store.add_message_pair(conversation_id, user_content=request.message, assistant_content=result.message)
            inferred = (request.message or "New Chat").strip().split("\n")[0][:60]
            await store.update_conversation_title_if_default(conversation_id, inferred)
            await store.summarize_if_needed(
                conversation_id,
                token_limit=int(request.token_limit or 128_000),
                target_ratio=float(request.summarize_target_ratio or 0.8),
                chat_model=rag_service.chat_model,
            )
        except Exception as e:
            print(f"⚠️ Conversation write/summarize failed: {e}")

        return response_obj
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def stream_chat_response(rag_service: HybridRAGService, request: ChatRequest, kwargs: Dict[str, Any]):
    """Stream chat response"""
    try:
        # Ensure conversation via MongoDB
        store = get_mongo_store()
        conversation_id = request.conversation_id
        if request.user_id:
            if not conversation_id:
                inferred = (request.message or "New Chat").strip().split("\n")[0][:60]
                conversation_id = await store.create_conversation(request.user_id, title=inferred, token_limit=request.token_limit or 128_000)
            else:
                convo = await store.get_conversation(conversation_id)
                if not convo or convo.get("user_id") != request.user_id:
                    raise HTTPException(status_code=403, detail="Forbidden")
        else:
            if not conversation_id:
                conversation_id = await store.create_conversation(user_id="anonymous", title="New Chat", token_limit=request.token_limit or 128_000)
        
        # Stream the response with Hybrid RAG service
        # Prepare prior history (user prompt + summaries + recent)
        prior_messages = None
        try:
            from langchain.schema import HumanMessage, AIMessage, SystemMessage
            prior_messages = []
            if request.user_id:
                active_prompt = await store.get_active_rag_prompt(request.user_id)
                if active_prompt and active_prompt.get("content"):
                    prior_messages.append(SystemMessage(content=str(active_prompt.get("content"))))
            summaries = await store.list_summaries(conversation_id)
            for s in summaries:
                prior_messages.append(SystemMessage(content=f"Conversation summary (layer {s.get('layer', 1)}): {s.get('summary_text', '')}"))
            history = await store.get_last_messages(conversation_id, limit=max(settings.chat_history_limit, 50))
            for m in history:
                if m.get("role") == "user":
                    prior_messages.append(HumanMessage(content=m.get("content", "")))
                elif m.get("role") == "assistant":
                    prior_messages.append(AIMessage(content=m.get("content", "")))
        except Exception:
            prior_messages = None

        async for chunk in rag_service.stream_chat(
            message=request.message,
            session_id=conversation_id,
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


@router.post("/conversations", response_model=ConversationInfo)
async def create_conversation(request: ConversationCreateRequest, current_user: dict = Depends(get_current_user)):
    if request.user_id and request.user_id != current_user.get("user_id"):
        raise HTTPException(status_code=403, detail="Forbidden")
    store = get_mongo_store()
    user_id = request.user_id or current_user.get("user_id")
    conversation_id = await store.create_conversation(user_id=user_id, title=request.title or "New Chat", token_limit=request.token_limit or 128_000)
    now = datetime.utcnow().isoformat()
    convo = await store.get_conversation(conversation_id)
    return ConversationInfo(
        conversation_id=conversation_id,
        user_id=user_id,
        title=convo.get("title", request.title or "New Chat"),
        created_at=convo.get("created_at", now),
        last_activity=convo.get("last_activity", now),
        message_count=int(convo.get("message_count", 0)),
        token_count_total=int(convo.get("token_count_total", 0)),
    )


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str, current_user: dict = Depends(get_current_user)):
    store = get_mongo_store()
    convo = await store.get_conversation(conversation_id)
    if not convo or convo.get("user_id") != current_user.get("user_id"):
        raise HTTPException(status_code=403, detail="Forbidden")
    msgs = await store.get_last_messages(conversation_id=conversation_id, limit=100)
    return {"conversation_id": conversation_id, "messages": msgs}


@router.post("/sessions")
async def deprecated_create_session():
    raise HTTPException(status_code=410, detail="Use /chat/conversations instead")


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(user_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """List conversations for the authenticated user"""
    try:
        store = get_mongo_store()
        uid = user_id or current_user.get("user_id")
        if uid != current_user.get("user_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
        convos = await store.list_conversations(uid)
        items = [
            ConversationInfo(
                conversation_id=c.get("conversation_id"),
                user_id=uid,
                title=c.get("title", "New Chat"),
                created_at=c.get("created_at", datetime.utcnow().isoformat()),
                last_activity=c.get("last_activity", datetime.utcnow().isoformat()),
                message_count=int(c.get("message_count", 0)),
                token_count_total=int(c.get("token_count_total", 0)),
            )
            for c in convos
        ]
        return ConversationListResponse(conversations=items, total=len(items))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    """Get conversation messages (after summarization deletions)."""
    try:
        store = get_mongo_store()
        convo = await store.get_conversation(conversation_id)
        if not convo or convo.get("user_id") != current_user.get("user_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
        msgs = await store.get_last_messages(conversation_id=conversation_id, limit=100)
        messages = [ChatMessageRequest(role=m.get("role"), content=m.get("content", "")) for m in msgs]
        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            messages=messages,
            title=convo.get("title", "Chat"),
            created_at=convo.get("created_at", datetime.utcnow().isoformat()),
            last_activity=convo.get("last_activity", datetime.utcnow().isoformat()),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a conversation and its messages/summaries."""
    try:
        store = get_mongo_store()
        convo = await store.get_conversation(conversation_id)
        if not convo or convo.get("user_id") != current_user.get("user_id"):
            raise HTTPException(status_code=403, detail="Forbidden")
        await store.db.messages.delete_many({"conversation_id": conversation_id})
        await store.db.summaries.delete_many({"conversation_id": conversation_id})
        await store.db.conversations.delete_one({"conversation_id": conversation_id})
        return {"message": "Conversation deleted successfully"}
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


# ---------- RAG Prompt Management Endpoints ----------

@router.get("/prompts", response_model=RAGPromptListResponse)
async def list_prompts(current_user: dict = Depends(get_current_user)):
    store = get_mongo_store()
    prompts = await store.list_rag_prompts(current_user.get("user_id"))
    items = [
        RAGPromptInfo(
            prompt_id=p.get("prompt_id"),
            name=p.get("name", "Unnamed"),
            content=p.get("content", ""),
            is_active=bool(p.get("is_active", False)),
            created_at=p.get("created_at", datetime.utcnow().isoformat()),
            updated_at=p.get("updated_at"),
        )
        for p in prompts
    ]
    return RAGPromptListResponse(prompts=items)


@router.post("/prompts", response_model=RAGPromptInfo)
async def create_prompt(request: RAGPromptCreate, current_user: dict = Depends(get_current_user)):
    store = get_mongo_store()
    res = await store.create_rag_prompt(current_user.get("user_id"), request.name, request.content, set_active=request.set_active)
    saved = await store.db.rag_prompts.find_one({"prompt_id": res["prompt_id"]}, {"_id": 0})
    return RAGPromptInfo(
        prompt_id=saved.get("prompt_id"),
        name=saved.get("name"),
        content=saved.get("content"),
        is_active=bool(saved.get("is_active", False)),
        created_at=saved.get("created_at"),
        updated_at=saved.get("updated_at"),
    )


@router.get("/prompts/active", response_model=RAGPromptActiveResponse)
async def get_active_prompt(current_user: dict = Depends(get_current_user)):
    store = get_mongo_store()
    p = await store.get_active_rag_prompt(current_user.get("user_id"))
    if not p:
        return RAGPromptActiveResponse(prompt=None)
    return RAGPromptActiveResponse(prompt=RAGPromptInfo(
        prompt_id=p.get("prompt_id"),
        name=p.get("name"),
        content=p.get("content"),
        is_active=bool(p.get("is_active", False)),
        created_at=p.get("created_at"),
        updated_at=p.get("updated_at"),
    ))


@router.post("/prompts/{prompt_id}/activate")
async def activate_prompt(prompt_id: str, current_user: dict = Depends(get_current_user)):
    store = get_mongo_store()
    await store.set_active_rag_prompt(current_user.get("user_id"), prompt_id)
    return {"message": "Prompt set as active"}


@router.patch("/prompts/{prompt_id}", response_model=RAGPromptInfo)
async def update_prompt(prompt_id: str, request: RAGPromptUpdate, current_user: dict = Depends(get_current_user)):
    store = get_mongo_store()
    await store.update_rag_prompt(current_user.get("user_id"), prompt_id, request.model_dump(exclude_unset=True))
    saved = await store.db.rag_prompts.find_one({"prompt_id": prompt_id}, {"_id": 0})
    if not saved or saved.get("user_id") != current_user.get("user_id"):
        raise HTTPException(status_code=404, detail="Prompt not found")
    return RAGPromptInfo(
        prompt_id=saved.get("prompt_id"),
        name=saved.get("name"),
        content=saved.get("content"),
        is_active=bool(saved.get("is_active", False)),
        created_at=saved.get("created_at"),
        updated_at=saved.get("updated_at"),
    )


@router.delete("/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str, current_user: dict = Depends(get_current_user)):
    store = get_mongo_store()
    saved = await store.db.rag_prompts.find_one({"prompt_id": prompt_id}, {"user_id": 1, "_id": 0})
    if not saved or saved.get("user_id") != current_user.get("user_id"):
        raise HTTPException(status_code=404, detail="Prompt not found")
    await store.delete_rag_prompt(current_user.get("user_id"), prompt_id)
    return {"message": "Prompt deleted"}