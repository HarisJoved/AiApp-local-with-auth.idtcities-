from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class EmbedderType(str, Enum):
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"


class VectorDBType(str, Enum):
    PINECONE = "pinecone"
    CHROMADB = "chromadb"
    QDRANT = "qdrant"


class OpenAIEmbedderConfig(BaseModel):
    api_key: str = Field(..., description="OpenAI API key")
    model_name: str = Field(default="text-embedding-ada-002", description="OpenAI embedding model")
    organization: Optional[str] = Field(None, description="OpenAI organization ID")
    timeout: int = Field(default=30, description="Request timeout in seconds")


class HuggingFaceEmbedderConfig(BaseModel):
    model_name: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="HuggingFace model name")
    device: str = Field(default="cpu", description="Device to run the model on")
    trust_remote_code: bool = Field(default=False, description="Trust remote code")
    cache_dir: Optional[str] = Field(None, description="Cache directory for models")


class EmbedderConfig(BaseModel):
    type: EmbedderType
    openai: Optional[OpenAIEmbedderConfig] = None
    huggingface: Optional[HuggingFaceEmbedderConfig] = None


class PineconeDBConfig(BaseModel):
    api_key: str = Field(..., description="Pinecone API key")
    environment: str = Field(..., description="Pinecone environment")
    index_name: str = Field(..., description="Pinecone index name")
    dimension: int = Field(default=384, description="Vector dimension")
    metric: str = Field(default="cosine", description="Distance metric")


class ChromaDBConfig(BaseModel):
    host: str = Field(default="localhost", description="ChromaDB host")
    port: int = Field(default=8000, description="ChromaDB port")
    collection_name: str = Field(default="documents", description="Collection name")
    persist_directory: Optional[str] = Field(None, description="Persist directory for local ChromaDB")


class QdrantDBConfig(BaseModel):
    host: str = Field(default="localhost", description="Qdrant host")
    port: int = Field(default=6333, description="Qdrant port")
    collection_name: str = Field(default="documents", description="Collection name")
    api_key: Optional[str] = Field(None, description="Qdrant API key")
    https: bool = Field(default=False, description="Use HTTPS")


class VectorDBConfig(BaseModel):
    type: VectorDBType
    pinecone: Optional[PineconeDBConfig] = None
    chromadb: Optional[ChromaDBConfig] = None
    qdrant: Optional[QdrantDBConfig] = None


class AppConfig(BaseModel):
    embedder: EmbedderConfig
    vector_db: VectorDBConfig
    max_file_size: int = Field(default=10 * 1024 * 1024, description="Max file size in bytes")
    chunk_size: int = Field(default=1000, description="Text chunk size for splitting")
    chunk_overlap: int = Field(default=200, description="Overlap between chunks") 