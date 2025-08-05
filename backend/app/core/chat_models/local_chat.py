"""
Local LLM Chat Model implementation supporting Transformers and Ollama.
"""

import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from .base import BaseChatModel, ChatMessage, ChatResponse


class LocalChatModel(BaseChatModel):
    """Local LLM chat model implementation (Ollama or Transformers)"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider = self.config.get("provider", "ollama")  # "ollama" or "transformers"
        self.model = self.config.get("model", "llama2")
        
        if self.provider == "transformers":
            self._initialize_transformers()
        elif self.provider == "ollama":
            self.ollama_url = self.config.get("ollama_url", "http://localhost:11434")
    
    def _validate_config(self) -> None:
        """Validate local model configuration"""
        if self.provider not in ["ollama", "transformers"]:
            raise ValueError("Local chat model provider must be 'ollama' or 'transformers'")
        
        if not self.config.get("model"):
            raise ValueError("Local chat model requires model name")
        
        if self.provider == "transformers":
            try:
                import torch
                import transformers
            except ImportError:
                raise ValueError("Transformers provider requires torch and transformers packages")
    
    def _initialize_transformers(self):
        """Initialize transformers model and tokenizer"""
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM, TextStreamer
            import torch
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model,
                trust_remote_code=self.config.get("trust_remote_code", True)
            )
            
            self.model_instance = AutoModelForCausalLM.from_pretrained(
                self.model,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                trust_remote_code=self.config.get("trust_remote_code", True)
            )
            
            # Add padding token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
        except Exception as e:
            raise RuntimeError(f"Failed to initialize transformers model: {str(e)}")
    
    async def generate_response(
        self, 
        messages: List[ChatMessage], 
        context: Optional[str] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate response using local model"""
        self.validate_messages(messages)
        
        if self.provider == "ollama":
            return await self._generate_ollama_response(messages, context, **kwargs)
        elif self.provider == "transformers":
            return await self._generate_transformers_response(messages, context, **kwargs)
    
    async def stream_response(
        self, 
        messages: List[ChatMessage], 
        context: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response using local model"""
        self.validate_messages(messages)
        
        if self.provider == "ollama":
            async for chunk in self._stream_ollama_response(messages, context, **kwargs):
                yield chunk
        elif self.provider == "transformers":
            async for chunk in self._stream_transformers_response(messages, context, **kwargs):
                yield chunk
    
    async def _generate_ollama_response(
        self, 
        messages: List[ChatMessage], 
        context: Optional[str] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate response using Ollama API"""
        prompt = self._convert_messages_to_prompt(messages, context)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.get("temperature", 0.7),
                "top_p": self.config.get("top_p", 1.0),
                "top_k": self.config.get("top_k", 40),
                "num_predict": self.config.get("max_tokens", 1000),
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status != 200:
                        raise RuntimeError(f"Ollama API error: {response.status}")
                    
                    result = await response.json()
                    
                    return ChatResponse(
                        message=result.get("response", ""),
                        usage={
                            "prompt_tokens": result.get("prompt_eval_count", 0),
                            "completion_tokens": result.get("eval_count", 0),
                            "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
                        },
                        model_info=f"Ollama {self.model}",
                        finish_reason="stop" if result.get("done") else "length"
                    )
        
        except Exception as e:
            raise RuntimeError(f"Ollama API error: {str(e)}")
    
    async def _stream_ollama_response(
        self, 
        messages: List[ChatMessage], 
        context: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response using Ollama API"""
        prompt = self._convert_messages_to_prompt(messages, context)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": self.config.get("temperature", 0.7),
                "top_p": self.config.get("top_p", 1.0),
                "top_k": self.config.get("top_k", 40),
                "num_predict": self.config.get("max_tokens", 1000),
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status != 200:
                        raise RuntimeError(f"Ollama API error: {response.status}")
                    
                    async for line in response.content:
                        if line:
                            try:
                                chunk = json.loads(line.decode().strip())
                                if chunk.get("response"):
                                    yield chunk["response"]
                                if chunk.get("done"):
                                    break
                            except json.JSONDecodeError:
                                continue
        
        except Exception as e:
            raise RuntimeError(f"Ollama streaming API error: {str(e)}")
    
    async def _generate_transformers_response(
        self, 
        messages: List[ChatMessage], 
        context: Optional[str] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate response using transformers"""
        import torch
        
        prompt = self._convert_messages_to_prompt(messages, context)
        
        # Tokenize input
        inputs = self.tokenizer.encode(prompt, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = inputs.to("cuda")
        
        # Generate response
        with torch.no_grad():
            outputs = await asyncio.to_thread(
                self.model_instance.generate,
                inputs,
                max_new_tokens=self.config.get("max_tokens", 1000),
                temperature=self.config.get("temperature", 0.7),
                top_p=self.config.get("top_p", 1.0),
                top_k=self.config.get("top_k", 40),
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        
        # Decode response
        response_text = self.tokenizer.decode(
            outputs[0][len(inputs[0]):], 
            skip_special_tokens=True
        )
        
        return ChatResponse(
            message=response_text.strip(),
            usage={
                "prompt_tokens": len(inputs[0]),
                "completion_tokens": len(outputs[0]) - len(inputs[0]),
                "total_tokens": len(outputs[0]),
            },
            model_info=f"Transformers {self.model}",
            finish_reason="stop"
        )
    
    async def _stream_transformers_response(
        self, 
        messages: List[ChatMessage], 
        context: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream response using transformers (simplified streaming)"""
        # Note: This is a simplified streaming implementation
        # For true streaming, you'd need to implement token-by-token generation
        response = await self._generate_transformers_response(messages, context, **kwargs)
        
        # Simulate streaming by yielding words
        words = response.message.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.05)  # Small delay to simulate streaming
    
    def _convert_messages_to_prompt(self, messages: List[ChatMessage], context: Optional[str] = None) -> str:
        """Convert ChatMessage objects to a prompt string"""
        prompt_parts = []
        
        # Add system instructions if context is provided (for RAG)
        if context and messages and messages[-1].role == "user":
            user_question = messages[-1].content
            rag_prompt = self.format_context_prompt(context, user_question)
            
            # Add conversation history (excluding the last user message)
            for msg in messages[:-1]:
                if msg.role == "user":
                    prompt_parts.append(f"User: {msg.content}")
                elif msg.role == "assistant":
                    prompt_parts.append(f"Assistant: {msg.content}")
                elif msg.role == "system":
                    prompt_parts.append(f"System: {msg.content}")
            
            # Add the RAG prompt
            prompt_parts.append(f"User: {rag_prompt}")
            prompt_parts.append("Assistant:")
        else:
            # Regular conversation without RAG
            for msg in messages:
                if msg.role == "user":
                    prompt_parts.append(f"User: {msg.content}")
                elif msg.role == "assistant":
                    prompt_parts.append(f"Assistant: {msg.content}")
                elif msg.role == "system":
                    prompt_parts.append(f"System: {msg.content}")
            
            # Add prompt for the assistant to respond
            prompt_parts.append("Assistant:")
        
        return "\n\n".join(prompt_parts)
    
    def get_model_info(self) -> str:
        """Get local model information"""
        return f"{self.provider.title()} {self.model}"
    
    def supports_streaming(self) -> bool:
        """Local models support streaming"""
        return True