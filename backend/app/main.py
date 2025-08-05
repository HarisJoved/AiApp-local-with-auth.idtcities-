import asyncio
from contextlib import asynccontextmanager
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import settings, config_manager
from app.services.factory import service_factory
from app.services.document_service import document_service
from app.routers import upload, config, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("Starting Document Embedding Platform...")
    
    # Load existing configuration
    await config_manager.load_config()
    
    # Initialize services if configuration exists
    current_config = config_manager.get_current_config()
    if current_config:
        try:
            embedder, vector_db = await service_factory.initialize_services(current_config)
            if embedder:
                document_service.set_embedder(embedder)
                print(f"Initialized embedder: {embedder.get_model_info()}")
            if vector_db:
                document_service.set_vector_db(vector_db)
                print("Initialized vector database")
        except Exception as e:
            print(f"Failed to initialize services: {e}")
    else:
        print("No configuration found. Please configure embedder and vector database.")
    
    print(f"Server starting on {settings.host}:{settings.port}")
    yield
    
    # Shutdown
    print("Shutting down Document Embedding Platform...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A modular document processing and embedding platform",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router)
app.include_router(config.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "configured": config_manager.is_configured(),
        "endpoints": {
            "upload": "/upload",
            "config": "/config",
            "search": "/upload/search",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "configured": config_manager.is_configured()
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    print(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    ) 