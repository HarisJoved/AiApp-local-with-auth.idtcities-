"""
Retrieval-Augmented Generation (RAG) service for document-aware chat.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from app.core.embedders.base import BaseEmbedder
from app.core.vector_db.base import BaseVectorDBClient
from app.core.chat_models.base import BaseChatModel, ChatMessage
from app.core.chat_models.base import ChatResponse as ModelChatResponse
from app.core.session.session_manager import SessionManager, ChatSession


class RAGResult:
    """Result of RAG pipeline execution"""
    
    def __init__(
        self,
        response: ModelChatResponse,
        retrieved_chunks: List[Dict[str, Any]],
        session: ChatSession,
        retrieval_time: float,
        generation_time: float
    ):
        self.response = response
        self.retrieved_chunks = retrieved_chunks
        self.session = session
        self.retrieval_time = retrieval_time
        self.generation_time = generation_time
        self.total_time = retrieval_time + generation_time


class RAGService:
    """Service for combining document retrieval with LLM generation"""
    
    def __init__(
        self,
        embedder: Optional[BaseEmbedder] = None,
        vector_db: Optional[BaseVectorDBClient] = None,
        chat_model: Optional[BaseChatModel] = None,
        session_manager: Optional[SessionManager] = None
    ):
        self.embedder = embedder
        self.vector_db = vector_db
        self.chat_model = chat_model
        self.session_manager = session_manager or SessionManager()
        
        # RAG configuration
        self.retrieval_config = {
            "top_k": 5,
            "similarity_threshold": 0.7,
            "max_context_length": 4000,
            "chunk_separator": "\n\n---\n\n"
        }
    
    def set_embedder(self, embedder: BaseEmbedder) -> None:
        """Set the embedder for document retrieval"""
        self.embedder = embedder
    
    def set_vector_db(self, vector_db: BaseVectorDBClient) -> None:
        """Set the vector database for document retrieval"""
        self.vector_db = vector_db
    
    def set_chat_model(self, chat_model: BaseChatModel) -> None:
        """Set the chat model for response generation"""
        self.chat_model = chat_model
    
    def update_retrieval_config(self, config: Dict[str, Any]) -> None:
        """Update retrieval configuration"""
        self.retrieval_config.update(config)
    
    async def chat(
        self,
        message: str,
        session_id: str,
        user_id: Optional[str] = None,
        use_rag: bool = True,
        **kwargs
    ) -> RAGResult:
        """
        Process a chat message with optional RAG
        
        Args:
            message: User's message/question
            session_id: Chat session ID
            user_id: Optional user ID
            use_rag: Whether to use document retrieval
            **kwargs: Additional parameters for chat model
        
        Returns:
            RAGResult with response and metadata
        """
        start_time = datetime.utcnow()
        
        # Validate required components
        if not self.chat_model:
            raise ValueError("Chat model not configured")
        
        # Get or create session
        session = await self.session_manager.get_session(session_id)
        if not session:
            session = await self.session_manager.create_session(user_id)
        
        # Add user message to session
        user_message = ChatMessage(role="user", content=message)
        session.add_message(user_message)
        
        # Retrieve relevant documents if RAG is enabled
        retrieved_chunks = []
        retrieval_time = 0.0
        context = None
        
        if use_rag and self.embedder and self.vector_db:
            retrieval_start = datetime.utcnow()
            retrieved_chunks = await self._retrieve_relevant_chunks(message)
            retrieval_end = datetime.utcnow()
            retrieval_time = (retrieval_end - retrieval_start).total_seconds()
            
            if retrieved_chunks:
                context = self._format_context(retrieved_chunks)
        
        # Get conversation history for context
        context_messages = session.get_context_messages(
            context_length=self.retrieval_config["max_context_length"]
        )
        
        # Generate response
        generation_start = datetime.utcnow()
        response = await self.chat_model.generate_response(
            messages=context_messages,
            context=context,
            **kwargs
        )
        generation_end = datetime.utcnow()
        generation_time = (generation_end - generation_start).total_seconds()
        
        # Add assistant response to session
        assistant_message = ChatMessage(
            role="assistant", 
            content=response.message,
            metadata={
                "model_info": response.model_info,
                "usage": response.usage,
                "retrieved_chunks": len(retrieved_chunks) if use_rag else 0
            }
        )
        session.add_message(assistant_message)
        
        # Save updated session
        await self.session_manager.save_session(session)
        
        return RAGResult(
            response=response,
            retrieved_chunks=retrieved_chunks,
            session=session,
            retrieval_time=retrieval_time,
            generation_time=generation_time
        )
    
    async def stream_chat(
        self,
        message: str,
        session_id: str,
        user_id: Optional[str] = None,
        use_rag: bool = True,
        **kwargs
    ):
        """
        Stream a chat response with optional RAG
        
        Args:
            message: User's message/question
            session_id: Chat session ID
            user_id: Optional user ID
            use_rag: Whether to use document retrieval
            **kwargs: Additional parameters for chat model
        
        Yields:
            Streaming response chunks
        """
        # Validate required components
        if not self.chat_model:
            raise ValueError("Chat model not configured")
        
        if not self.chat_model.supports_streaming():
            raise ValueError("Chat model does not support streaming")
        
        # Get or create session
        session = await self.session_manager.get_session(session_id)
        if not session:
            session = await self.session_manager.create_session(user_id)
        
        # Add user message to session
        user_message = ChatMessage(role="user", content=message)
        session.add_message(user_message)
        
        # Retrieve relevant documents if RAG is enabled
        context = None
        if use_rag and self.embedder and self.vector_db:
            retrieved_chunks = await self._retrieve_relevant_chunks(message)
            if retrieved_chunks:
                context = self._format_context(retrieved_chunks)
        
        # Get conversation history for context
        context_messages = session.get_context_messages(
            context_length=self.retrieval_config["max_context_length"]
        )
        
        # Stream response
        full_response = ""
        async for chunk in self.chat_model.stream_response(
            messages=context_messages,
            context=context,
            **kwargs
        ):
            full_response += chunk
            yield chunk
        
        # Add complete assistant response to session
        assistant_message = ChatMessage(
            role="assistant", 
            content=full_response,
            metadata={
                "model_info": self.chat_model.get_model_info(),
                "streaming": True
            }
        )
        session.add_message(assistant_message)
        
        # Save updated session
        await self.session_manager.save_session(session)
    
    async def _retrieve_relevant_chunks(self, query: str) -> List[Dict[str, Any]]:
        """Retrieve relevant document chunks for the query"""
        try:
            # Generate query embedding
            query_embedding = await self.embedder.embed_text(query)
            
            # Search vector database
            search_results = await self.vector_db.search(
                query_embedding=query_embedding,
                top_k=self.retrieval_config["top_k"],
                similarity_threshold=self.retrieval_config["similarity_threshold"]
            )
            
            return search_results
        
        except Exception as e:
            print(f"Error during document retrieval: {e}")
            return []
    
    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into context string"""
        if not chunks:
            return ""
        
        context_parts = []
        total_length = 0
        max_length = self.retrieval_config["max_context_length"]
        
        for chunk in chunks:
            content = chunk.get("content", "")
            metadata = chunk.get("metadata", {})
            
            # Add source information if available
            source_info = ""
            if metadata.get("source"):
                source_info = f"[Source: {metadata['source']}]"
            
            formatted_chunk = f"{source_info}\n{content}" if source_info else content
            
            # Check if adding this chunk would exceed max length
            if total_length + len(formatted_chunk) > max_length:
                break
            
            context_parts.append(formatted_chunk)
            total_length += len(formatted_chunk)
        
        return self.retrieval_config["chunk_separator"].join(context_parts)
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a chat session"""
        return await self.session_manager.get_session(session_id)
    
    async def list_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List chat sessions"""
        return await self.session_manager.list_sessions(user_id)
    
    async def delete_session(self, session_id: str) -> None:
        """Delete a chat session"""
        await self.session_manager.delete_session(session_id)
    
    async def create_session(self, user_id: Optional[str] = None, title: Optional[str] = None) -> ChatSession:
        """Create a new chat session"""
        return await self.session_manager.create_session(user_id, title)
    
    def is_ready(self) -> Tuple[bool, List[str]]:
        """Check if RAG service is ready to use"""
        missing_components = []
        
        if not self.chat_model:
            missing_components.append("chat_model")
        
        # RAG components are optional
        if not self.embedder:
            missing_components.append("embedder (optional for RAG)")
        
        if not self.vector_db:
            missing_components.append("vector_db (optional for RAG)")
        
        return len(missing_components) == 0 or "chat_model" not in [c.split(" ")[0] for c in missing_components], missing_components