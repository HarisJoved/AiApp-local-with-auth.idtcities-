import asyncio
from typing import List, Dict, Any
import torch
from sentence_transformers import SentenceTransformer

from app.models.config import HuggingFaceEmbedderConfig
from .base import BaseEmbedder


class HuggingFaceEmbedder(BaseEmbedder):
    """HuggingFace sentence transformers implementation"""
    
    def __init__(self, config: HuggingFaceEmbedderConfig):
        super().__init__()
        self.config = config
        self.model_name = config.model_name
        self.device = config.device
        
        # Load the model
        self.model = SentenceTransformer(
            self.model_name,
            device=self.device,
            trust_remote_code=config.trust_remote_code,
            cache_folder=config.cache_dir
        )
        
        # Get model dimension
        self._dimension = self.model.get_sentence_embedding_dimension()
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, 
                lambda: self.model.encode([text], convert_to_tensor=False)[0]
            )
            return embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
        except Exception as e:
            raise RuntimeError(f"Failed to generate HuggingFace embedding: {str(e)}")
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.model.encode(texts, convert_to_tensor=False, show_progress_bar=len(texts) > 10)
            )
            
            # Convert to list of lists
            if hasattr(embeddings, 'tolist'):
                return embeddings.tolist()
            else:
                return [list(emb) for emb in embeddings]
        except Exception as e:
            raise RuntimeError(f"Failed to generate HuggingFace embeddings: {str(e)}")
    
    def get_dimension(self) -> int:
        """Get the dimension of the embeddings"""
        return self._dimension
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model"""
        return {
            "provider": "huggingface",
            "model_name": self.model_name,
            "dimension": self.get_dimension(),
            "device": self.device,
            "max_seq_length": getattr(self.model, 'max_seq_length', 512),
            "trust_remote_code": self.config.trust_remote_code
        } 