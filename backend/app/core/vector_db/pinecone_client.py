import asyncio
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec

from app.models.config import PineconeDBConfig
from app.models.document import DocumentChunk
from app.models.search import SearchResult
from .base import BaseVectorDBClient


class PineconeClient(BaseVectorDBClient):
    """Pinecone vector database client"""
    
    def __init__(self, config: PineconeDBConfig):
        super().__init__()
        self.config = config
        self.pc = Pinecone(api_key=config.api_key)
        self.index_name = config.index_name
        self.dimension = config.dimension
        self.metric = config.metric
        self.index = None
    
    async def initialize(self) -> bool:
        """Initialize Pinecone connection and create index if needed"""
        try:
            # Check if index exists
            existing_indexes = self.pc.list_indexes()
            index_names = [idx['name'] for idx in existing_indexes.get('indexes', [])]
            
            if self.index_name not in index_names:
                # Create index if it doesn't exist
                await self.create_collection(self.dimension, self.metric)
            
            # Connect to index
            self.index = self.pc.Index(self.index_name)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Pinecone: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check if Pinecone is accessible"""
        try:
            if not self.index:
                await self.initialize()
            
            # Try to get index stats
            stats = self.index.describe_index_stats()
            return True
        except Exception:
            return False
    
    async def create_collection(self, dimension: int, metric: str = "cosine") -> bool:
        """Create a new Pinecone index"""
        try:
            self.pc.create_index(
                name=self.index_name,
                dimension=dimension,
                metric=metric,
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"  # Adjust as needed
                )
            )
            
            # Wait for index to be ready
            import time
            while True:
                try:
                    desc = self.pc.describe_index(self.index_name)
                    if desc['status']['ready']:
                        break
                    time.sleep(1)
                except:
                    time.sleep(1)
            
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to create Pinecone index: {str(e)}")
    
    async def delete_collection(self) -> bool:
        """Delete the Pinecone index"""
        try:
            self.pc.delete_index(self.index_name)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete Pinecone index: {str(e)}")
    
    async def upsert_vectors(self, chunks: List[DocumentChunk]) -> bool:
        """Upsert vectors to Pinecone"""
        try:
            if not self.index:
                await self.initialize()
            
            # Prepare vectors for upsert
            vectors = []
            for chunk in chunks:
                if chunk.embedding:
                    vectors.append({
                        "id": chunk.id,
                        "values": chunk.embedding,
                        "metadata": {
                            **chunk.metadata,
                            "content": chunk.content[:1000]  # Limit content size
                        }
                    })
            
            if vectors:
                self.index.upsert(vectors=vectors)
            
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to upsert vectors to Pinecone: {str(e)}")
    
    async def search_vectors(
        self, 
        query_vector: List[float], 
        top_k: int = 5, 
        threshold: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar vectors in Pinecone"""
        try:
            if not self.index:
                await self.initialize()
            
            # Perform search
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True,
                filter=filter_metadata
            )
            
            # Convert to SearchResult objects
            search_results = []
            for match in results.matches:
                if match.score >= threshold:
                    metadata = match.metadata or {}
                    search_results.append(SearchResult(
                        chunk_id=match.id,
                        document_id=metadata.get("filename", "unknown"),
                        content=metadata.get("content", ""),
                        score=match.score,
                        metadata=metadata
                    ))
            
            return search_results
        except Exception as e:
            raise RuntimeError(f"Failed to search vectors in Pinecone: {str(e)}")
    
    async def delete_vectors(self, chunk_ids: List[str]) -> bool:
        """Delete vectors from Pinecone"""
        try:
            if not self.index:
                await self.initialize()
            
            self.index.delete(ids=chunk_ids)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete vectors from Pinecone: {str(e)}")
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get Pinecone index statistics"""
        try:
            if not self.index:
                await self.initialize()
            
            stats = self.index.describe_index_stats()
            return {
                "total_vectors": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": stats.namespaces
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get Pinecone stats: {str(e)}") 