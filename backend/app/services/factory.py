from typing import Optional

from app.models.config import AppConfig, EmbedderType, VectorDBType
from app.core.embedders.base import BaseEmbedder
from app.core.embedders.openai_embedder import OpenAIEmbedder
from app.core.embedders.huggingface_embedder import HuggingFaceEmbedder
from app.core.vector_db.base import BaseVectorDBClient
from app.core.vector_db.pinecone_client import PineconeClient
from app.core.vector_db.chromadb_client import ChromaDBClient
from app.core.vector_db.qdrant_client import QdrantDBClient


class ServiceFactory:
    """Factory for creating embedder and vector database instances"""
    
    @staticmethod
    def create_embedder(config: AppConfig) -> Optional[BaseEmbedder]:
        """Create embedder instance based on configuration"""
        try:
            embedder_config = config.embedder
            
            if embedder_config.type == EmbedderType.OPENAI:
                if not embedder_config.openai:
                    raise ValueError("OpenAI configuration is required")
                return OpenAIEmbedder(embedder_config.openai)
            
            elif embedder_config.type == EmbedderType.HUGGINGFACE:
                if not embedder_config.huggingface:
                    raise ValueError("HuggingFace configuration is required")
                return HuggingFaceEmbedder(embedder_config.huggingface)
            
            else:
                raise ValueError(f"Unsupported embedder type: {embedder_config.type}")
                
        except Exception as e:
            print(f"Failed to create embedder: {e}")
            return None
    
    @staticmethod
    def create_vector_db(config: AppConfig) -> Optional[BaseVectorDBClient]:
        """Create vector database client based on configuration"""
        try:
            vector_db_config = config.vector_db
            
            if vector_db_config.type == VectorDBType.PINECONE:
                if not vector_db_config.pinecone:
                    raise ValueError("Pinecone configuration is required")
                return PineconeClient(vector_db_config.pinecone)
            
            elif vector_db_config.type == VectorDBType.CHROMADB:
                if not vector_db_config.chromadb:
                    raise ValueError("ChromaDB configuration is required")
                return ChromaDBClient(vector_db_config.chromadb)
            
            elif vector_db_config.type == VectorDBType.QDRANT:
                if not vector_db_config.qdrant:
                    raise ValueError("Qdrant configuration is required")
                return QdrantDBClient(vector_db_config.qdrant)
            
            else:
                raise ValueError(f"Unsupported vector database type: {vector_db_config.type}")
                
        except Exception as e:
            print(f"Failed to create vector database client: {e}")
            return None
    
    @staticmethod
    async def initialize_services(config: AppConfig) -> tuple[Optional[BaseEmbedder], Optional[BaseVectorDBClient]]:
        """Initialize both embedder and vector database services"""
        embedder = ServiceFactory.create_embedder(config)
        vector_db = ServiceFactory.create_vector_db(config)
        
        # Initialize vector database
        if vector_db:
            try:
                await vector_db.initialize()
                
                # Create collection if embedder is available
                if embedder:
                    dimension = embedder.get_dimension()
                    # Check if collection exists by trying to get stats
                    try:
                        stats = await vector_db.get_collection_stats()
                        # If collection exists but has wrong dimension, warn user
                        if hasattr(vector_db, 'dimension') and vector_db.dimension != dimension:
                            print(f"Warning: Vector DB dimension ({vector_db.dimension}) doesn't match embedder dimension ({dimension})")
                    except:
                        # Collection doesn't exist, create it
                        await vector_db.create_collection(dimension)
                        
            except Exception as e:
                print(f"Failed to initialize vector database: {e}")
                vector_db = None
        
        return embedder, vector_db


# Global factory instance
service_factory = ServiceFactory() 