from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple

from app.models.document import DocumentChunk
from app.models.search import SearchResult


class BaseVectorDBClient(ABC):
    """Abstract base class for vector database clients"""
    
    def __init__(self, **kwargs):
        self.config = kwargs
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the vector database connection and create collection if needed"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the vector database is healthy and accessible"""
        pass
    
    @abstractmethod
    async def create_collection(self, dimension: int, metric: str = "cosine") -> bool:
        """Create a new collection/index with specified dimension and metric"""
        pass
    
    @abstractmethod
    async def delete_collection(self) -> bool:
        """Delete the collection/index"""
        pass
    
    @abstractmethod
    async def upsert_vectors(self, chunks: List[DocumentChunk]) -> bool:
        """Insert or update vectors in the database"""
        pass
    
    @abstractmethod
    async def search_vectors(
        self, 
        query_vector: List[float], 
        top_k: int = 5, 
        threshold: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar vectors"""
        pass
    
    @abstractmethod
    async def delete_vectors(self, chunk_ids: List[str]) -> bool:
        """Delete vectors by their IDs"""
        pass
    
    @abstractmethod
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        pass
    
    async def search(
        self, 
        query_embedding: List[float], 
        top_k: int = 5, 
        similarity_threshold: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors (RAG-compatible interface)
        
        This method provides a simplified interface for the RAG service.
        It maps to the search_vectors method and returns results in a format
        expected by the RAG pipeline.
        """
        try:
            # Call the concrete implementation's search_vectors method
            search_results = await self.search_vectors(
                query_vector=query_embedding,
                top_k=top_k,
                threshold=similarity_threshold,
                filter_metadata=filter_metadata
            )
            
            # Convert SearchResult objects to dictionaries for RAG compatibility
            formatted_results = []
            for result in search_results:
                formatted_results.append({
                    "content": result.content,
                    "score": result.score,
                    "metadata": {
                        **result.metadata,
                        "chunk_id": result.chunk_id,
                        "document_id": result.document_id
                    }
                })
            
            return formatted_results
        except Exception as e:
            raise RuntimeError(f"Failed to search vectors: {str(e)}")

    async def batch_upsert_vectors(self, chunks: List[DocumentChunk], batch_size: int = 100) -> bool:
        """Upsert vectors in batches to avoid memory/network issues"""
        try:
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                success = await self.upsert_vectors(batch)
                if not success:
                    return False
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to batch upsert vectors: {str(e)}") 