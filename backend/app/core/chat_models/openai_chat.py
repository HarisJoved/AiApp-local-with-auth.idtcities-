"""
OpenAI Chat Model implementation supporting GPT models.
"""

import openai
from typing import List, Dict, Any, Optional, AsyncGenerator
from .base import BaseChatModel, ChatMessage, ChatResponse


class OpenAIChatModel(BaseChatModel):
    """OpenAI GPT chat model implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = openai.AsyncOpenAI(
            api_key=self.config.get("api_key"),
            organization=self.config.get("organization")
        )
        self.model = self.config.get("model", "gpt-3.5-turbo")
    
    def _validate_config(self) -> None:
        """Validate OpenAI configuration"""
        required_fields = ["api_key"]
        for field in required_fields:
            if not self.config.get(field):
                raise ValueError(f"OpenAI chat model requires {field}")
    
    async def generate_response(
        self, 
        messages: List[ChatMessage], 
        context: Optional[str] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate response using OpenAI Chat Completions API"""
        self.validate_messages(messages)
        
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages(messages, context)
        
        # Set up parameters
        params = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": self.config.get("temperature", 0.7),
            "max_tokens": self.config.get("max_tokens", 1000),
            "top_p": self.config.get("top_p", 1.0),
            "frequency_penalty": self.config.get("frequency_penalty", 0.0),
            "presence_penalty": self.config.get("presence_penalty", 0.0),
        }
        
        # Add any additional kwargs
        params.update(kwargs)
        
        try:
            response = await self.client.chat.completions.create(**params)
            
            return ChatResponse(
                message=response.choices[0].message.content,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                model_info=response.model,
                finish_reason=response.choices[0].finish_reason
            )
        
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")
    
    async def stream_response(
        self, 
        messages: List[ChatMessage], 
        context: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response using OpenAI Chat Completions API"""
        self.validate_messages(messages)
        
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages(messages, context)
        
        # Set up parameters
        params = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": self.config.get("temperature", 0.7),
            "max_tokens": self.config.get("max_tokens", 1000),
            "top_p": self.config.get("top_p", 1.0),
            "frequency_penalty": self.config.get("frequency_penalty", 0.0),
            "presence_penalty": self.config.get("presence_penalty", 0.0),
            "stream": True,
        }
        
        # Add any additional kwargs
        params.update(kwargs)
        
        try:
            stream = await self.client.chat.completions.create(**params)
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        except Exception as e:
            raise RuntimeError(f"OpenAI streaming API error: {str(e)}")
    
    def _convert_messages(self, messages: List[ChatMessage], context: Optional[str] = None) -> List[Dict[str, str]]:
        """Convert ChatMessage objects to OpenAI message format"""
        openai_messages = []
        
        # Add system message if context is provided (for RAG)
        if context and messages and messages[-1].role == "user":
            # Create RAG prompt with context
            user_question = messages[-1].content
            rag_prompt = self.format_context_prompt(context, user_question)
            
            # Add system message with context
            openai_messages.append({
                "role": "system",
                "content": "You are a helpful assistant that answers questions based on provided document context. Always cite specific information from the context when possible."
            })
            
            # Add conversation history (excluding the last user message)
            for msg in messages[:-1]:
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Replace the last user message with RAG prompt
            openai_messages.append({
                "role": "user",
                "content": rag_prompt
            })
        else:
            # Regular conversation without RAG
            for msg in messages:
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        return openai_messages
    
    def get_model_info(self) -> str:
        """Get OpenAI model information"""
        return f"OpenAI {self.model}"
    
    def supports_streaming(self) -> bool:
        """OpenAI supports streaming"""
        return True