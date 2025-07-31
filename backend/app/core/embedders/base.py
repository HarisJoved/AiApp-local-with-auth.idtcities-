from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseEmbedder(ABC):
    """Abstract base class for text embedders"""
    
    def __init__(self, **kwargs):
        self.config = kwargs
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        pass
    
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get the dimension of the embeddings"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model"""
        pass
    
    async def health_check(self) -> bool:
        """Check if the embedder is healthy and working"""
        try:
            test_embedding = await self.embed_text("test")
            return len(test_embedding) == self.get_dimension()
        except Exception:
            return False 