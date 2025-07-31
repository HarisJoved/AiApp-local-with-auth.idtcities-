import asyncio
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

from app.models.config import ChromaDBConfig
from app.models.document import DocumentChunk
from app.models.search import SearchResult
from .base import BaseVectorDBClient


class ChromaDBClient(BaseVectorDBClient):
    """ChromaDB vector database client"""
    
    def __init__(self, config: ChromaDBConfig):
        super().__init__()
        self.config = config
        self.collection_name = config.collection_name
        self.client = None
        self.collection = None
    
    async def initialize(self) -> bool:
        """Initialize ChromaDB connection"""
        try:
            if self.config.persist_directory:
                # Local persistent ChromaDB
                self.client = chromadb.PersistentClient(
                    path=self.config.persist_directory
                )
            else:
                # Remote ChromaDB
                self.client = chromadb.HttpClient(
                    host=self.config.host,
                    port=self.config.port
                )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(self.collection_name)
            except Exception:
                # Collection doesn't exist, create it
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Document embeddings collection"}
                )
            
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize ChromaDB: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check if ChromaDB is accessible"""
        try:
            if not self.client:
                await self.initialize()
            
            # Try to list collections
            collections = self.client.list_collections()
            return True
        except Exception:
            return False
    
    async def create_collection(self, dimension: int, metric: str = "cosine") -> bool:
        """Create a new ChromaDB collection"""
        try:
            if not self.client:
                await self.initialize()
            
            # Delete existing collection if it exists
            try:
                self.client.delete_collection(self.collection_name)
            except Exception:
                pass  # Collection doesn't exist
            
            # Create new collection
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={
                    "description": "Document embeddings collection",
                    "dimension": dimension,
                    "metric": metric
                }
            )
            
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to create ChromaDB collection: {str(e)}")
    
    async def delete_collection(self) -> bool:
        """Delete the ChromaDB collection"""
        try:
            if not self.client:
                await self.initialize()
            
            self.client.delete_collection(self.collection_name)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete ChromaDB collection: {str(e)}")
    
    async def upsert_vectors(self, chunks: List[DocumentChunk]) -> bool:
        """Upsert vectors to ChromaDB"""
        try:
            if not self.collection:
                await self.initialize()
            
            # Prepare data for upsert
            ids = []
            embeddings = []
            metadatas = []
            documents = []
            
            for chunk in chunks:
                if chunk.embedding:
                    ids.append(chunk.id)
                    embeddings.append(chunk.embedding)
                    metadatas.append(chunk.metadata)
                    documents.append(chunk.content)
            
            if ids:
                self.collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents
                )
            
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to upsert vectors to ChromaDB: {str(e)}")
    
    async def search_vectors(
        self, 
        query_vector: List[float], 
        top_k: int = 5, 
        threshold: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Search for similar vectors in ChromaDB"""
        try:
            if not self.collection:
                await self.initialize()
            
            # Perform search
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
                where=filter_metadata,
                include=["metadatas", "documents", "distances"]
            )
            
            # Convert to SearchResult objects
            search_results = []
            if results["ids"]:
                for i, chunk_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i]
                    score = 1 - distance  # Convert distance to similarity score
                    
                    if score >= threshold:
                        metadata = results["metadatas"][0][i] or {}
                        content = results["documents"][0][i] or ""
                        
                        search_results.append(SearchResult(
                            chunk_id=chunk_id,
                            document_id=metadata.get("filename", "unknown"),
                            content=content,
                            score=score,
                            metadata=metadata
                        ))
            
            return search_results
        except Exception as e:
            raise RuntimeError(f"Failed to search vectors in ChromaDB: {str(e)}")
    
    async def delete_vectors(self, chunk_ids: List[str]) -> bool:
        """Delete vectors from ChromaDB"""
        try:
            if not self.collection:
                await self.initialize()
            
            self.collection.delete(ids=chunk_ids)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete vectors from ChromaDB: {str(e)}")
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get ChromaDB collection statistics"""
        try:
            if not self.collection:
                await self.initialize()
            
            count = self.collection.count()
            return {
                "total_vectors": count,
                "collection_name": self.collection_name,
                "metadata": self.collection.metadata
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get ChromaDB stats: {str(e)}") 