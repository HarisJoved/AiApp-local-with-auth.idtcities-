from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.models.config import EmbedderConfig, VectorDBConfig, ChatModelConfig, AppConfig
from app.config.settings import config_manager
from app.services.factory import service_factory
from app.services.document_service import document_service


router = APIRouter(prefix="/config", tags=["configuration"])


@router.get("/")
async def get_current_config():
    """Get current application configuration"""
    try:
        config = config_manager.get_current_config()
        if not config:
            return {"message": "No configuration found", "configured": False}
        
        return {
            "configured": True,
            "config": config.model_dump()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")


@router.post("/embedder")
async def update_embedder_config(embedder_config: EmbedderConfig):
    """Update embedder configuration"""
    try:
        # Get current config or create default vector DB config
        current_config = config_manager.get_current_config()
        if current_config and current_config.vector_db:
            vector_db_config = current_config.vector_db
        else:
            # Create default ChromaDB config
            from app.models.config import VectorDBConfig, VectorDBType, ChromaDBConfig
            vector_db_config = VectorDBConfig(
                type=VectorDBType.CHROMADB,
                chromadb=ChromaDBConfig()
            )
        
        # Validate configuration by trying to create embedder
        temp_config = AppConfig(
            embedder=embedder_config,
            vector_db=vector_db_config,
            max_file_size=10*1024*1024,
            chunk_size=1000,
            chunk_overlap=200
        )
        
        embedder = service_factory.create_embedder(temp_config)
        if not embedder:
            raise HTTPException(status_code=400, detail="Invalid embedder configuration")
        
        # Test embedder health
        is_healthy = await embedder.health_check()
        if not is_healthy:
            raise HTTPException(status_code=400, detail="Embedder health check failed")
        
        # Save configuration
        success = await config_manager.update_embedder_config(embedder_config)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save embedder configuration")
        
        # Reset chat service to pick up new configuration
        try:
            from app.routers.chat import reset_rag_service
            reset_rag_service()
        except ImportError:
            pass  # Chat service might not be loaded yet
        
        # Update document service
        document_service.set_embedder(embedder)
        
        return {
            "message": "Embedder configuration updated successfully",
            "embedder_info": embedder.get_model_info()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update embedder config: {str(e)}")


@router.post("/vector-db")
async def update_vector_db_config(vector_db_config: VectorDBConfig):
    """Update vector database configuration"""
    try:
        # Get current config or create default embedder config
        current_config = config_manager.get_current_config()
        if current_config and current_config.embedder:
            embedder_config = current_config.embedder
        else:
            # Create default HuggingFace embedder config
            from app.models.config import EmbedderConfig, EmbedderType, HuggingFaceEmbedderConfig
            embedder_config = EmbedderConfig(
                type=EmbedderType.HUGGINGFACE,
                huggingface=HuggingFaceEmbedderConfig()
            )
        
        # Validate configuration by trying to create vector DB client
        temp_config = AppConfig(
            embedder=embedder_config,
            vector_db=vector_db_config,
            max_file_size=10*1024*1024,
            chunk_size=1000,
            chunk_overlap=200
        )
        
        vector_db = service_factory.create_vector_db(temp_config)
        if not vector_db:
            raise HTTPException(status_code=400, detail="Invalid vector database configuration")
        
        # Test vector database health
        await vector_db.initialize()
        is_healthy = await vector_db.health_check()
        if not is_healthy:
            raise HTTPException(status_code=400, detail="Vector database health check failed")
        
        # Save configuration
        success = await config_manager.update_vector_db_config(vector_db_config)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save vector database configuration")
        
        # Reset chat service to pick up new configuration
        try:
            from app.routers.chat import reset_rag_service
            reset_rag_service()
        except ImportError:
            pass  # Chat service might not be loaded yet
        
        # Update document service
        document_service.set_vector_db(vector_db)
        
        # Get stats
        try:
            stats = await vector_db.get_collection_stats()
        except:
            stats = {"message": "Collection not yet created"}
        
        return {
            "message": "Vector database configuration updated successfully",
            "stats": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update vector DB config: {str(e)}")


@router.post("/complete")
async def update_complete_config(config: AppConfig):
    """Update complete application configuration"""
    try:
        # Initialize services with new configuration
        embedder, vector_db = await service_factory.initialize_services(config)
        
        if not embedder:
            raise HTTPException(status_code=400, detail="Failed to initialize embedder")
        
        if not vector_db:
            raise HTTPException(status_code=400, detail="Failed to initialize vector database")
        
        # Save configuration
        success = await config_manager.save_config(config)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save configuration")
        
        # Update document service
        document_service.set_embedder(embedder)
        document_service.set_vector_db(vector_db)
        
        return {
            "message": "Configuration updated successfully",
            "embedder_info": embedder.get_model_info(),
            "vector_db_stats": await vector_db.get_collection_stats()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update complete config: {str(e)}")


@router.get("/health")
async def check_service_health():
    """Check health of configured services"""
    try:
        config = config_manager.get_current_config()
        if not config:
            return {"configured": False, "message": "No configuration found"}
        
        health_status = {
            "configured": True,
            "embedder": {"healthy": False, "info": None},
            "vector_db": {"healthy": False, "stats": None}
        }
        
        # Check embedder health
        if document_service.embedder:
            try:
                embedder_healthy = await document_service.embedder.health_check()
                health_status["embedder"]["healthy"] = embedder_healthy
                health_status["embedder"]["info"] = document_service.embedder.get_model_info()
            except Exception as e:
                health_status["embedder"]["error"] = str(e)
        
        # Check vector database health
        if document_service.vector_db:
            try:
                vector_db_healthy = await document_service.vector_db.health_check()
                health_status["vector_db"]["healthy"] = vector_db_healthy
                if vector_db_healthy:
                    health_status["vector_db"]["stats"] = await document_service.vector_db.get_collection_stats()
            except Exception as e:
                health_status["vector_db"]["error"] = str(e)
        
        return health_status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check service health: {str(e)}")


@router.delete("/reset")
async def reset_configuration():
    """Reset configuration to default values"""
    try:
        # Create default configuration
        config_manager._app_config = None
        default_config = config_manager._create_default_config()
        
        # Initialize services with default configuration
        embedder, vector_db = await service_factory.initialize_services(default_config)
        
        # Update document service
        if embedder:
            document_service.set_embedder(embedder)
        if vector_db:
            document_service.set_vector_db(vector_db)
        
        # Save default configuration
        await config_manager.save_config(default_config)
        
        return {"message": "Configuration reset to default values"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset configuration: {str(e)}")


@router.post("/chat-model")
async def update_chat_model_config(chat_model_config: ChatModelConfig):
    """Update chat model configuration"""
    try:
        # Get current config or create a minimal one
        current_config = config_manager.get_current_config()
        if not current_config:
            # Need embedder and vector DB to create a valid config
            from app.models.config import (
                EmbedderConfig, EmbedderType, HuggingFaceEmbedderConfig,
                VectorDBConfig, VectorDBType, ChromaDBConfig
            )
            embedder_config = EmbedderConfig(
                type=EmbedderType.HUGGINGFACE,
                huggingface=HuggingFaceEmbedderConfig()
            )
            vector_db_config = VectorDBConfig(
                type=VectorDBType.CHROMADB,
                chromadb=ChromaDBConfig()
            )
            current_config = AppConfig(
                embedder=embedder_config,
                vector_db=vector_db_config
            )
        
        # Validate configuration by creating chat model
        temp_config = AppConfig(
            embedder=current_config.embedder,
            vector_db=current_config.vector_db,
            chat_model=chat_model_config,
            max_file_size=current_config.max_file_size,
            chunk_size=current_config.chunk_size,
            chunk_overlap=current_config.chunk_overlap
        )
        
        chat_model = service_factory.create_chat_model(temp_config)
        if not chat_model:
            raise ValueError("Failed to create chat model with provided configuration")
        
        # Update configuration
        new_config = AppConfig(
            embedder=current_config.embedder,
            vector_db=current_config.vector_db,
            chat_model=chat_model_config,
            max_file_size=current_config.max_file_size,
            chunk_size=current_config.chunk_size,
            chunk_overlap=current_config.chunk_overlap,
            rag_top_k=current_config.rag_top_k if hasattr(current_config, 'rag_top_k') else 5,
            rag_similarity_threshold=current_config.rag_similarity_threshold if hasattr(current_config, 'rag_similarity_threshold') else 0.7,
            rag_max_context_length=current_config.rag_max_context_length if hasattr(current_config, 'rag_max_context_length') else 4000,
            session_storage_type=current_config.session_storage_type if hasattr(current_config, 'session_storage_type') else "memory",
            session_storage_path=current_config.session_storage_path if hasattr(current_config, 'session_storage_path') else "sessions",
            session_max_age_days=current_config.session_max_age_days if hasattr(current_config, 'session_max_age_days') else 30
        )
        
        await config_manager.save_config(new_config)
        
        # Reset chat service to pick up new configuration
        try:
            from app.routers.chat import reset_rag_service
            reset_rag_service()
        except ImportError:
            pass  # Chat service might not be loaded yet
        
        return {
            "message": "Chat model configuration updated successfully",
            "chat_model_info": chat_model.get_model_info()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update chat model config: {str(e)}")


@router.get("/chat-model")
async def get_chat_model_config():
    """Get current chat model configuration"""
    try:
        config = config_manager.get_current_config()
        if not config or not config.chat_model:
            return {"message": "No chat model configuration found", "configured": False}
        
        return {
            "configured": True,
            "config": config.chat_model.model_dump()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat model config: {str(e)}")


@router.delete("/chat-model")
async def remove_chat_model_config():
    """Remove chat model configuration"""
    try:
        current_config = config_manager.get_current_config()
        if not current_config:
            raise HTTPException(status_code=404, detail="No configuration found")
        
        # Create new config without chat model
        new_config = AppConfig(
            embedder=current_config.embedder,
            vector_db=current_config.vector_db,
            chat_model=None,
            max_file_size=current_config.max_file_size,
            chunk_size=current_config.chunk_size,
            chunk_overlap=current_config.chunk_overlap
        )
        
        await config_manager.save_config(new_config)
        
        return {"message": "Chat model configuration removed"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove chat model config: {str(e)}")


@router.post("/rag")
async def update_rag_config(
    top_k: int = 5,
    similarity_threshold: float = 0.7,
    max_context_length: int = 4000
):
    """Update RAG (Retrieval-Augmented Generation) configuration"""
    try:
        current_config = config_manager.get_current_config()
        if not current_config:
            raise HTTPException(status_code=404, detail="No configuration found")
        
        # Update RAG settings
        new_config = AppConfig(
            embedder=current_config.embedder,
            vector_db=current_config.vector_db,
            chat_model=current_config.chat_model,
            max_file_size=current_config.max_file_size,
            chunk_size=current_config.chunk_size,
            chunk_overlap=current_config.chunk_overlap,
            rag_top_k=top_k,
            rag_similarity_threshold=similarity_threshold,
            rag_max_context_length=max_context_length,
            session_storage_type=current_config.session_storage_type if hasattr(current_config, 'session_storage_type') else "memory",
            session_storage_path=current_config.session_storage_path if hasattr(current_config, 'session_storage_path') else "sessions",
            session_max_age_days=current_config.session_max_age_days if hasattr(current_config, 'session_max_age_days') else 30
        )
        
        await config_manager.save_config(new_config)
        
        # Reset chat service to pick up new configuration
        try:
            from app.routers.chat import reset_rag_service
            reset_rag_service()
        except ImportError:
            pass  # Chat service might not be loaded yet
        
        return {
            "message": "RAG configuration updated successfully",
            "config": {
                "top_k": top_k,
                "similarity_threshold": similarity_threshold,
                "max_context_length": max_context_length
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update RAG config: {str(e)}")


@router.post("/reset-chat-service")
async def reset_chat_service():
    """Reset the chat service to reinitialize with current configuration"""
    try:
        from app.routers.chat import reset_rag_service
        reset_rag_service()
        return {"message": "Chat service reset successfully"}
    except ImportError:
        raise HTTPException(status_code=503, detail="Chat service not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset chat service: {str(e)}") 