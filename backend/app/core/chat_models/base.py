"""
Abstract base class for chat models supporting various LLM providers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Represents a single chat message"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Response from chat model"""
    message: str
    usage: Optional[Dict[str, Any]] = None
    model_info: Optional[str] = None
    finish_reason: Optional[str] = None


class BaseChatModel(ABC):
    """Abstract base class for chat models"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize chat model with configuration"""
        self.config = config
        self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate the provided configuration"""
        pass
    
    @abstractmethod
    async def generate_response(
        self, 
        messages: List[ChatMessage], 
        context: Optional[str] = None,
        **kwargs
    ) -> ChatResponse:
        """
        Generate a response from the chat model
        
        Args:
            messages: List of chat messages (conversation history)
            context: Additional context (e.g., retrieved document chunks)
            **kwargs: Additional model-specific parameters
        
        Returns:
            ChatResponse with generated message
        """
        pass
    
    @abstractmethod
    async def stream_response(
        self, 
        messages: List[ChatMessage], 
        context: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream response tokens from the chat model
        
        Args:
            messages: List of chat messages (conversation history)
            context: Additional context (e.g., retrieved document chunks)
            **kwargs: Additional model-specific parameters
        
        Yields:
            Response tokens as they are generated
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> str:
        """Get information about the current model"""
        pass
    
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Check if the model supports streaming responses"""
        pass
    
    def format_context_prompt(self, context: str, user_question: str) -> str:
        """
        Format the context and user question into a prompt for RAG
        
        Args:
            context: Retrieved document context
            user_question: User's question
        
        Returns:
            Formatted prompt string
        """
        return f"""Based on the following context from the documents, please answer the user's question. If the answer cannot be found in the provided context, please say so clearly.

Context:
{context}

Question: {user_question}

Answer:"""
    
    def validate_messages(self, messages: List[ChatMessage]) -> None:
        """Validate message format and content"""
        if not messages:
            raise ValueError("Messages list cannot be empty")
        
        valid_roles = {"user", "assistant", "system"}
        for msg in messages:
            if msg.role not in valid_roles:
                raise ValueError(f"Invalid message role: {msg.role}")
            if not msg.content.strip():
                raise ValueError("Message content cannot be empty")