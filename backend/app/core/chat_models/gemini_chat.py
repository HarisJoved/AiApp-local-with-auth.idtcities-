"""
Google Gemini Chat Model implementation.
"""

import google.generativeai as genai
from typing import List, Dict, Any, Optional, AsyncGenerator
from .base import BaseChatModel, ChatMessage, ChatResponse


class GeminiChatModel(BaseChatModel):
    """Google Gemini chat model implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        genai.configure(api_key=self.config.get("api_key"))
        self.model_name = self.config.get("model", "gemini-pro")
        self.model = genai.GenerativeModel(self.model_name)
    
    def _validate_config(self) -> None:
        """Validate Gemini configuration"""
        required_fields = ["api_key"]
        for field in required_fields:
            if not self.config.get(field):
                raise ValueError(f"Gemini chat model requires {field}")
    
    async def generate_response(
        self, 
        messages: List[ChatMessage], 
        context: Optional[str] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate response using Gemini API"""
        self.validate_messages(messages)
        
        # Convert messages to Gemini format
        prompt = self._convert_messages_to_prompt(messages, context)
        
        # Set up generation config
        generation_config = genai.types.GenerationConfig(
            temperature=self.config.get("temperature", 0.7),
            max_output_tokens=self.config.get("max_tokens", 1000),
            top_p=self.config.get("top_p", 1.0),
            top_k=self.config.get("top_k", 40),
        )
        
        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=generation_config,
                stream=False
            )
            
            return ChatResponse(
                message=response.text,
                usage={
                    "prompt_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
                    "total_tokens": response.usage_metadata.total_token_count if response.usage_metadata else 0,
                },
                model_info=self.model_name,
                finish_reason=response.candidates[0].finish_reason.name if response.candidates else None
            )
        
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {str(e)}")
    
    async def stream_response(
        self, 
        messages: List[ChatMessage], 
        context: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response using Gemini API"""
        self.validate_messages(messages)
        
        # Convert messages to Gemini format
        prompt = self._convert_messages_to_prompt(messages, context)
        
        # Set up generation config
        generation_config = genai.types.GenerationConfig(
            temperature=self.config.get("temperature", 0.7),
            max_output_tokens=self.config.get("max_tokens", 1000),
            top_p=self.config.get("top_p", 1.0),
            top_k=self.config.get("top_k", 40),
        )
        
        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=generation_config,
                stream=True
            )
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        
        except Exception as e:
            raise RuntimeError(f"Gemini streaming API error: {str(e)}")
    
    def _convert_messages_to_prompt(self, messages: List[ChatMessage], context: Optional[str] = None) -> str:
        """Convert ChatMessage objects to a Gemini-compatible prompt"""
        prompt_parts = []
        
        # Add system instructions if context is provided (for RAG)
        if context and messages and messages[-1].role == "user":
            user_question = messages[-1].content
            rag_prompt = self.format_context_prompt(context, user_question)
            
            # Add conversation history (excluding the last user message)
            for msg in messages[:-1]:
                if msg.role == "user":
                    prompt_parts.append(f"Human: {msg.content}")
                elif msg.role == "assistant":
                    prompt_parts.append(f"Assistant: {msg.content}")
                elif msg.role == "system":
                    prompt_parts.append(f"System: {msg.content}")
            
            # Add the RAG prompt
            prompt_parts.append(f"Human: {rag_prompt}")
            prompt_parts.append("Assistant:")
        else:
            # Regular conversation without RAG
            for msg in messages:
                if msg.role == "user":
                    prompt_parts.append(f"Human: {msg.content}")
                elif msg.role == "assistant":
                    prompt_parts.append(f"Assistant: {msg.content}")
                elif msg.role == "system":
                    prompt_parts.append(f"System: {msg.content}")
            
            # Add prompt for the assistant to respond
            prompt_parts.append("Assistant:")
        
        return "\n\n".join(prompt_parts)
    
    def get_model_info(self) -> str:
        """Get Gemini model information"""
        return f"Google {self.model_name}"
    
    def supports_streaming(self) -> bool:
        """Gemini supports streaming"""
        return True