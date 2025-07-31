from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.models.config import EmbedderConfig, VectorDBConfig, AppConfig
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