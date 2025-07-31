import asyncio
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from app.models.config import QdrantDBConfig
from app.models.document import DocumentChunk
from app.models.search import SearchResult
from .base import BaseVectorDBClient


class QdrantDBClient(BaseVectorDBClient):
    """Qdrant vector database client"""
    
    def __init__(self, config: QdrantDBConfig):
        super().__init__()
        self.config = config
        self.collection_name = config.collection_name
        self.client = None
        
        # Distance metric mapping
        self.distance_map = {
            "cosine": Distance.COSINE,
            "euclidean": Distance.EUCLID,
            "dot": Distance.DOT
        }
    
    async def initialize(self) -> bool:
        """Initialize Qdrant connection"""
        try:
            self.client = AsyncQdrantClient(
                host=self.config.host,
                port=self.config.port,
                api_key=self.config.api_key,
                https=self.config.https
            )
            
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Qdrant: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check if Qdrant is accessible"""
        try:
            if not self.client:
                await self.initialize()
            
            # Try to get collections info
            collections = await self.client.get_collections()
            return True
        except Exception:
            return False
    
    async def create_collection(self, dimension: int, metric: str = "cosine") -> bool:
        """Create a new Qdrant collection"""
        try:
            if not self.client:
                await self.initialize()
            
            # Check if collection exists
            try:
                await self.client.get_collection(self.collection_name)
                # Collection exists, delete it first
                await self.client.delete_collection(self.collection_name)
            except Exception:
                pass  # Collection doesn't exist
            
            # Create new collection
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=dimension,
                    distance=self.distance_map.get(metric, Distance.COSINE)
                )
            )
            
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to create Qdrant collection: {str(e)}")
    
    async def delete_collection(self) -> bool:
        """Delete the Qdrant collection"""
        try:
            if not self.client:
                await self.initialize()
            
            await self.client.delete_collection(self.collection_name)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete Qdrant collection: {str(e)}")
    
    async def upsert_vectors(self, chunks: List[DocumentChunk]) -> bool:
        """Upsert vectors to Qdrant"""
        try:
            if not self.client:
                await self.initialize()
            
            # Prepare points for upsert
            points = []
            for chunk in chunks:
                if chunk.embedding:
                    point = PointStruct(
                        id=chunk.id,
                        vector=chunk.embedding,
                        payload={
                            **chunk.metadata,
                            "content": chunk.content
                        }
                    )
                    points.append(point)
            
            if points:
                await self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
            
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to upsert vectors to Qdrant: {str(e)}")
    
    async def search_vectors(
        self, 
        query_vector: List[float], 
        top_k: int = 5, 
        threshold: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar vectors in Qdrant"""
        try:
            if not self.client:
                await self.initialize()
            
            # Prepare filter if provided
            query_filter = None
            if filter_metadata:
                conditions = []
                for key, value in filter_metadata.items():
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
                query_filter = Filter(must=conditions)
            
            # Perform search
            results = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=threshold,
                query_filter=query_filter,
                with_payload=True
            )
            
            # Convert to SearchResult objects
            search_results = []
            for result in results:
                payload = result.payload or {}
                search_results.append(SearchResult(
                    chunk_id=str(result.id),
                    document_id=payload.get("filename", "unknown"),
                    content=payload.get("content", ""),
                    score=result.score,
                    metadata=payload
                ))
            
            return search_results
        except Exception as e:
            raise RuntimeError(f"Failed to search vectors in Qdrant: {str(e)}")
    
    async def delete_vectors(self, chunk_ids: List[str]) -> bool:
        """Delete vectors from Qdrant"""
        try:
            if not self.client:
                await self.initialize()
            
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=chunk_ids
            )
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete vectors from Qdrant: {str(e)}")
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get Qdrant collection statistics"""
        try:
            if not self.client:
                await self.initialize()
            
            info = await self.client.get_collection(self.collection_name)
            return {
                "total_vectors": info.points_count,
                "vectors_config": info.config.params.vectors,
                "status": info.status
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get Qdrant stats: {str(e)}") 