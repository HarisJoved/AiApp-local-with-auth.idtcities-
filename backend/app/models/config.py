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
    batch_size: int = Field(default=100, description="Batch size for processing multiple texts")
    max_retries: int = Field(default=3, description="Maximum number of retries for failed requests")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    dimensions: Optional[int] = Field(None, description="Vector dimensions (auto-detected if not specified)")
    strip_new_lines: bool = Field(default=True, description="Strip new lines from input text")
    skip_empty: bool = Field(default=True, description="Skip empty texts")


class HuggingFaceEmbedderConfig(BaseModel):
    model_name: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", description="HuggingFace model name")
    device: str = Field(default="cpu", description="Device to run the model on")
    trust_remote_code: bool = Field(default=False, description="Trust remote code")
    cache_dir: Optional[str] = Field(None, description="Cache directory for models")
    batch_size: int = Field(default=32, description="Batch size for processing multiple texts")
    max_seq_length: Optional[int] = Field(None, description="Maximum sequence length (auto-detected if not specified)")
    dimensions: Optional[int] = Field(None, description="Vector dimensions (auto-detected if not specified)")
    normalize_embeddings: bool = Field(default=False, description="Normalize embeddings to unit length")
    show_progress_bar: bool = Field(default=False, description="Show progress bar during encoding")
    convert_to_numpy: bool = Field(default=True, description="Convert output to numpy arrays")
    convert_to_tensor: bool = Field(default=False, description="Convert output to tensors")
    device_map: Optional[str] = Field(None, description="Device mapping for multi-GPU setups")
    model_kwargs: Optional[Dict[str, Any]] = Field(default=None, description="Additional model arguments")
    encode_kwargs: Optional[Dict[str, Any]] = Field(default=None, description="Additional encoding arguments")


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