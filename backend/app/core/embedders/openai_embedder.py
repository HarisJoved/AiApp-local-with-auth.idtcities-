import asyncio
from typing import List, Dict, Any
from openai import AsyncOpenAI

from app.models.config import OpenAIEmbedderConfig
from .base import BaseEmbedder


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI embeddings implementation"""
    
    def __init__(self, config: OpenAIEmbedderConfig):
        super().__init__()
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            organization=config.organization,
            timeout=config.timeout
        )
        self.model_name = config.model_name
        
        # Model dimension mapping
        self.model_dimensions = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            response = await self.client.embeddings.create(
                model=self.model_name,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise RuntimeError(f"Failed to generate OpenAI embedding: {str(e)}")
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        try:
            # OpenAI has a limit on batch size, so we might need to chunk
            batch_size = 100  # Adjust based on OpenAI limits
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = await self.client.embeddings.create(
                    model=self.model_name,
                    input=batch
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
        except Exception as e:
            raise RuntimeError(f"Failed to generate OpenAI embeddings: {str(e)}")
    
    def get_dimension(self) -> int:
        """Get the dimension of the embeddings"""
        return self.model_dimensions.get(self.model_name, 1536)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the embedding model"""
        return {
            "provider": "openai",
            "model_name": self.model_name,
            "dimension": self.get_dimension(),
            "max_tokens": 8191,  # OpenAI embedding models limit
            "api_version": "v1"
        } 