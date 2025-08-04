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
            # Filter texts based on configuration
            if self.config.skip_empty:
                texts = [text for text in texts if text.strip()]
            
            if self.config.strip_new_lines:
                texts = [text.replace('\n', ' ').replace('\r', ' ') for text in texts]
            
            # Use configured batch size
            batch_size = self.config.batch_size
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                # Prepare request parameters
                request_params = {
                    'model': self.model_name,
                    'input': batch
                }
                
                # Add dimensions if specified (for newer models)
                if self.config.dimensions and self.model_name in ['text-embedding-3-small', 'text-embedding-3-large']:
                    request_params['dimensions'] = self.config.dimensions
                
                response = await self.client.embeddings.create(**request_params)
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