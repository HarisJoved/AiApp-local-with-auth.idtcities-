"""
LangChain-based RAG service for document-aware chat.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain_community.vectorstores import Pinecone as LangChainPinecone
from langchain_community.vectorstores import Chroma as LangChainChroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.callbacks.base import BaseCallbackHandler

from pydantic import BaseModel

from app.models.config import AppConfig, EmbedderType, VectorDBType, ChatModelType
from app.core.session.session_manager import SessionManager, ChatSession


class ChatResult(BaseModel):
    """Result of a chat interaction"""
    message: str
    session_id: str  # used as memory key; now conversation_id is passed here
    model_info: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    retrieved_chunks: List[Dict[str, Any]] = []
    retrieval_time: float = 0.0
    generation_time: float = 0.0
    total_time: float = 0.0
    debug: Optional[Dict[str, Any]] = None


class StreamingCallbackHandler(BaseCallbackHandler):
    """Callback handler for streaming responses"""
    
    def __init__(self):
        self.tokens = []
        
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Handle new token"""
        self.tokens.append(token)
        
    def get_response(self) -> str:
        """Get the complete response"""
        return "".join(self.tokens)


class LangChainRAGService:
    """LangChain-based RAG service for document-aware chat"""
    
    def __init__(self, config: AppConfig, session_manager: SessionManager):
        self.config = config
        self.session_manager = session_manager
        
        # Initialize components
        self.embeddings = None
        self.vectorstore = None
        self.chat_model = None
        self.retrieval_qa = None
        
        # RAG configuration
        self.retrieval_config = {
            "top_k": config.rag_top_k or 5,
            "similarity_threshold": config.rag_similarity_threshold or 0.0,
            "max_context_length": config.rag_max_context_length or 4000
        }
        
        # Conversation memories (per session)
        self.memories: Dict[str, ConversationBufferWindowMemory] = {}
        # Store the RAG prompt text for debugging
        self.rag_prompt_template_str: Optional[str] = None
    
    async def initialize(self) -> bool:
        """Initialize all RAG components"""
        try:
            print("  LangChain RAG Service - Starting initialization...")
            print(f"  Config check - Embedder: {bool(self.config.embedder)}")
            print(f"  Config check - Vector DB: {bool(self.config.vector_db)}")
            print(f"  Config check - Chat Model: {bool(self.config.chat_model)}")
            
            print("  Initializing embeddings...")
            await self._initialize_embeddings()
            print(f"  ✅ Embeddings initialized: {type(self.embeddings).__name__}")
            
            print("  Initializing vectorstore...")
            await self._initialize_vectorstore()
            print(f"  ✅ Vectorstore initialized: {type(self.vectorstore).__name__}")
            
            print("  Initializing chat model...")
            await self._initialize_chat_model()
            print(f"  ✅ Chat model initialized: {type(self.chat_model).__name__}")
            
            print("  Initializing RAG chain...")
            await self._initialize_rag_chain()
            print("  ✅ RAG chain initialized")
            
            # Final check
            is_ready, missing = self.is_ready()
            print(f"  Final check - Ready: {is_ready}, Missing: {missing}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize LangChain RAG service: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _initialize_embeddings(self):
        """Initialize embeddings based on configuration"""
        if not self.config.embedder:
            raise ValueError("Embedder configuration is missing")
            
        embedder_config = self.config.embedder
        print(f"    Embedder type: {embedder_config.type}")
        
        if embedder_config.type == EmbedderType.OPENAI:
            if not embedder_config.openai:
                raise ValueError("OpenAI embedder configuration required")
            
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=embedder_config.openai.api_key,
                model=embedder_config.openai.model,
                dimensions=embedder_config.openai.dimensions if embedder_config.openai.dimensions else None
            )
            
        elif embedder_config.type == EmbedderType.HUGGINGFACE:
            if not embedder_config.huggingface:
                raise ValueError("HuggingFace embedder configuration required")
            
            model_kwargs = embedder_config.huggingface.model_kwargs or {}
            encode_kwargs = embedder_config.huggingface.encode_kwargs or {}
            
            self.embeddings = HuggingFaceEmbeddings(
                model_name=embedder_config.huggingface.model_name,
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs
            )
        else:
            raise ValueError(f"Unsupported embedder type: {embedder_config.type}")
    
    async def _initialize_vectorstore(self):
        """Initialize vectorstore based on configuration"""
        if not self.embeddings:
            raise ValueError("Embeddings must be initialized first")
            
        vector_db_config = self.config.vector_db
        print(f"    Initializing vectorstore for type: {vector_db_config.type}")
        
        if vector_db_config.type == VectorDBType.PINECONE:
            if not vector_db_config.pinecone:
                raise ValueError("Pinecone configuration required")
            
            from pinecone import Pinecone
            from langchain_pinecone import PineconeVectorStore
            
            print(f"    Pinecone config: index={vector_db_config.pinecone.index_name}")
            
            # Initialize Pinecone client and pass it to the vectorstore
            pc = Pinecone(api_key=vector_db_config.pinecone.api_key)
            
            # Set environment variable for LangChain compatibility
            import os
            os.environ['PINECONE_API_KEY'] = vector_db_config.pinecone.api_key
            
            # Check if index exists and has data
            try:
                index = pc.Index(vector_db_config.pinecone.index_name)
                stats = index.describe_index_stats()
                print(f"    Pinecone index stats: {stats}")
            except Exception as e:
                print(f"    Error checking Pinecone index: {e}")
            
            # Use existing index with custom retriever
            self.vectorstore = PineconeVectorStore.from_existing_index(
                index_name=vector_db_config.pinecone.index_name,
                embedding=self.embeddings,
                text_key="content"  # Use content field from metadata
            )
            
        elif vector_db_config.type == VectorDBType.CHROMADB:
            if not vector_db_config.chromadb:
                raise ValueError("ChromaDB configuration required")
            
            from langchain_chroma import Chroma
            
            print(f"    ChromaDB config: collection={vector_db_config.chromadb.collection_name}, persist_dir={vector_db_config.chromadb.persist_directory}")
            
            self.vectorstore = Chroma(
                collection_name=vector_db_config.chromadb.collection_name,
                embedding_function=self.embeddings,
                persist_directory=vector_db_config.chromadb.persist_directory
            )
            
            # Check if collection has data
            try:
                count = self.vectorstore.collection.count()
                print(f"    ChromaDB collection count: {count}")
            except Exception as e:
                print(f"    Error checking ChromaDB collection: {e}")
            
        else:
            raise ValueError(f"Unsupported vector database type: {vector_db_config.type}")
    
    async def _initialize_chat_model(self):
        """Initialize chat model based on configuration"""
        if not self.config.chat_model:
            raise ValueError("Chat model configuration is missing")
            
        chat_config = self.config.chat_model
        print(f"    Chat model type: {chat_config.type}")
        
        if chat_config.type == ChatModelType.OPENAI:
            if not chat_config.openai:
                raise ValueError("OpenAI chat configuration required")
            
            self.chat_model = ChatOpenAI(
                openai_api_key=chat_config.openai.api_key,
                model_name=chat_config.openai.model,
                temperature=chat_config.openai.temperature,
                max_tokens=chat_config.openai.max_tokens,
                streaming=True
            )
            
        elif chat_config.type == ChatModelType.GEMINI:
            if not chat_config.gemini:
                raise ValueError("Gemini chat configuration required")
            
            self.chat_model = ChatGoogleGenerativeAI(
                google_api_key=chat_config.gemini.api_key,
                model=chat_config.gemini.model,
                temperature=chat_config.gemini.temperature,
                max_output_tokens=chat_config.gemini.max_tokens
            )
            
        else:
            raise ValueError(f"Unsupported chat model type: {chat_config.type}")
    
    async def _initialize_rag_chain(self):
        """Initialize the RAG chain"""
        if not self.vectorstore or not self.chat_model:
            raise ValueError("Vectorstore and chat model must be initialized first")
        
        # Create retriever with proper search parameters
        retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": self.retrieval_config["top_k"]}
        )
        
        # Create RAG prompt template
        rag_prompt = PromptTemplate.from_template("""
You are a helpful AI assistant. Use the following context from documents to answer the user's question.
If you don't know the answer based on the context, just say so.
 
Context:
{context}
 
Conversation History:
{chat_history}
 
Question: {question}
 
Answer:""")
        # Save instruction-only prompt for debugging (exclude variable placeholders)
        try:
            self.rag_prompt_template_str = (
                "You are a helpful AI assistant. Use the following context from documents to answer the user's question. "
                "If you don't know the answer based on the context, just say so."
            )
        except Exception:
            self.rag_prompt_template_str = ""
        
        # Create conversational retrieval chain
        self.retrieval_qa = ConversationalRetrievalChain.from_llm(
            llm=self.chat_model,
            retriever=retriever,
            combine_docs_chain_kwargs={"prompt": rag_prompt},
            return_source_documents=True,
            verbose=True
        )
    
    def _get_memory(self, session_id: str) -> ConversationBufferWindowMemory:
        """Get or create conversation memory for session"""
        if session_id not in self.memories:
            self.memories[session_id] = ConversationBufferWindowMemory(
                k=10,  # Keep last 10 exchanges
                return_messages=True,
                memory_key="chat_history"
            )
        return self.memories[session_id]
    
    async def chat(
        self,
        message: str,
        session_id: str,
        user_id: Optional[str] = None,
        use_rag: bool = True,
        chat_history_override: Optional[List[BaseMessage]] = None,
        **kwargs
    ) -> ChatResult:
        """
        Process a chat message with optional RAG
        
        Args:
            message: User's message/question
            session_id: Chat session ID
            user_id: Optional user ID
            use_rag: Whether to use document retrieval
            **kwargs: Additional parameters for chat model
        
        Returns:
            ChatResult with response and metadata
        """
        start_time = datetime.utcnow()
        
        if not self.chat_model:
            raise ValueError("Chat model not initialized")
        
        # Get or create session
        session = await self.session_manager.get_session(session_id)
        if not session:
            session = await self.session_manager.create_session(user_id)
        
        retrieved_chunks = []
        retrieval_time = 0.0
        
        try:
            if use_rag and self.retrieval_qa and self.vectorstore:
                # Debug: Check if vectorstore has documents
                try:
                    # Try to get document count
                    if hasattr(self.vectorstore, 'index'):
                        # Pinecone
                        stats = await asyncio.to_thread(self.vectorstore.index.describe_index_stats)
                        total_vectors = stats.get('total_vector_count', 0)
                        print(f"🔍 Vectorstore has {total_vectors} vectors")
                    elif hasattr(self.vectorstore, 'collection'):
                        # ChromaDB
                        count = await asyncio.to_thread(self.vectorstore.collection.count)
                        print(f"🔍 Vectorstore has {count} documents")
                    else:
                        print("🔍 Vectorstore type not recognized for counting")
                except Exception as e:
                    print(f"🔍 Error checking vectorstore: {e}")
                
                # Use RAG with LangChain
                retrieval_start = datetime.utcnow()
                
                # Get conversation memory
                memory = self._get_memory(session_id)
                
                # Debug: Test direct retrieval
                try:
                    retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
                    docs = await asyncio.to_thread(retriever.get_relevant_documents, message)
                    print(f"🔍 Direct retrieval found {len(docs)} documents")
                    for i, doc in enumerate(docs):
                        print(f"  Doc {i}: {doc.page_content[:100]}...")
                except Exception as e:
                    print(f"🔍 Error in direct retrieval: {e}")
                
                # Determine chat history source
                chat_history = chat_history_override if chat_history_override is not None else memory.chat_memory.messages
                # Run the retrieval QA chain
                result = await asyncio.to_thread(
                    self.retrieval_qa,
                    {
                        "question": message,
                        "chat_history": chat_history,
                    }
                )
                
                retrieval_end = datetime.utcnow()
                retrieval_time = (retrieval_end - retrieval_start).total_seconds()
                
                response_text = result["answer"]
                
                # Extract retrieved chunks
                if "source_documents" in result:
                    retrieved_chunks = [
                        {
                            "content": doc.page_content,
                            "score": 1.0,  # LangChain doesn't always provide scores
                            "metadata": doc.metadata
                        }
                        for doc in result["source_documents"]
                    ]
                    print(f"🔍 Retrieved {len(retrieved_chunks)} chunks from chain")
                else:
                    print("🔍 No source_documents in result")
                
                # Update memory
                memory.save_context(
                    {"input": message},
                    {"output": response_text}
                )
                
            else:
                # Simple chat without RAG
                generation_start = datetime.utcnow()
                
                messages = [HumanMessage(content=message)]
                response = await asyncio.to_thread(self.chat_model.invoke, messages)
                response_text = response.content
                
                generation_end = datetime.utcnow()
                retrieval_time = 0.0
            
            end_time = datetime.utcnow()
            total_time = (end_time - start_time).total_seconds()
            generation_time = total_time - retrieval_time
            
            # Update session history
            from app.core.chat_models.base import ChatMessage
            user_message = ChatMessage(role="user", content=message)
            assistant_message = ChatMessage(
                role="assistant", 
                content=response_text,
                metadata={
                    "retrieved_chunks": len(retrieved_chunks),
                    "use_rag": use_rag
                }
            )
            
            session.add_message(user_message)
            session.add_message(assistant_message)
            await self.session_manager.save_session(session)
            
            # Prepare debug info
            debug_payload: Dict[str, Any] = {
                "base_prompt": self.rag_prompt_template_str,
                "retriever_top_k": self.retrieval_config.get("top_k"),
            }
            try:
                if chat_history_override is not None:
                    debug_payload["used_chat_history"] = [
                        {"type": type(m).__name__, "content": getattr(m, 'content', str(m))}
                        for m in chat_history_override
                    ]
                else:
                    debug_payload["used_chat_history"] = [
                        {"type": type(m).__name__, "content": getattr(m, 'content', str(m))}
                        for m in memory.chat_memory.messages
                    ]
            except Exception:
                pass

            return ChatResult(
                message=response_text,
                session_id=session.session_id,
                model_info=self._get_model_info(),
                usage=self._get_usage_info(),
                retrieved_chunks=retrieved_chunks,
                retrieval_time=retrieval_time,
                generation_time=generation_time,
                total_time=total_time,
                debug=debug_payload
            )
            
        except Exception as e:
            print(f"Error in LangChain RAG chat: {e}")
            raise
    
    async def stream_chat(
        self,
        message: str,
        session_id: str,
        user_id: Optional[str] = None,
        use_rag: bool = True,
        chat_history_override: Optional[List[BaseMessage]] = None,
        **kwargs
    ):
        """
        Stream chat response
        
        Args:
            message: User's message/question
            session_id: Chat session ID
            user_id: Optional user ID
            use_rag: Whether to use document retrieval
            **kwargs: Additional parameters for chat model
        
        Yields:
            Response chunks as they are generated
        """
        if not self.chat_model:
            raise ValueError("Chat model not initialized")
        
        # Get or create session
        session = await self.session_manager.get_session(session_id)
        if not session:
            session = await self.session_manager.create_session(user_id)
        
        try:
            if use_rag and self.retrieval_qa and self.vectorstore:
                # Create streaming callback
                streaming_handler = StreamingCallbackHandler()
                
                # Get conversation memory
                memory = self._get_memory(session_id)
                
                # Run retrieval QA with streaming
                def run_chain():
                    return self.retrieval_qa(
                        {
                            "question": message,
                            "chat_history": chat_history_override if chat_history_override is not None else memory.buffer,
                        },
                        callbacks=[streaming_handler]
                    )
                
                # Run in thread to avoid blocking
                result = await asyncio.to_thread(run_chain)
                
                # Stream the response
                response_text = result["answer"]
                for i, char in enumerate(response_text):
                    yield char
                    if i % 10 == 0:  # Add small delays for streaming effect
                        await asyncio.sleep(0.01)
                
                # Update memory
                memory.save_context(
                    {"input": message},
                    {"output": response_text}
                )
                
            else:
                # Simple streaming chat without RAG
                messages = [HumanMessage(content=message)]
                
                response_text = ""
                async for chunk in self.chat_model.astream(messages):
                    if hasattr(chunk, 'content'):
                        char = chunk.content
                        response_text += char
                        yield char
            
            # Update session history
            from app.core.chat_models.base import ChatMessage
            user_message = ChatMessage(role="user", content=message)
            assistant_message = ChatMessage(
                role="assistant", 
                content=response_text,
                metadata={"use_rag": use_rag}
            )
            
            session.add_message(user_message)
            session.add_message(assistant_message)
            await self.session_manager.save_session(session)
            
        except Exception as e:
            print(f"Error in LangChain RAG streaming: {e}")
            yield f"Error: {str(e)}"
    
    def _get_model_info(self) -> str:
        """Get model information"""
        if not self.chat_model:
            return "Unknown"
        
        model_type = type(self.chat_model).__name__
        if hasattr(self.chat_model, 'model_name'):
            return f"{model_type}: {self.chat_model.model_name}"
        elif hasattr(self.chat_model, 'model'):
            return f"{model_type}: {self.chat_model.model}"
        else:
            return model_type
    
    def _get_usage_info(self) -> Dict[str, Any]:
        """Get usage information (if available)"""
        # LangChain doesn't always provide detailed usage info
        return {"provider": "langchain"}
    
    def is_ready(self) -> Tuple[bool, List[str]]:
        """Check if the service is ready"""
        missing = []
        
        if not self.embeddings:
            missing.append("embeddings")
        if not self.vectorstore:
            missing.append("vectorstore")
        if not self.chat_model:
            missing.append("chat_model")
        if not self.retrieval_qa:
            missing.append("retrieval_chain")
        
        return len(missing) == 0, missing
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get session by ID"""
        return await self.session_manager.get_session(session_id)
    
    async def list_sessions(self, user_id: Optional[str] = None) -> List[ChatSession]:
        """List sessions"""
        return await self.session_manager.list_sessions(user_id)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        if session_id in self.memories:
            del self.memories[session_id]
        return await self.session_manager.delete_session(session_id)
    
    async def create_session(self, user_id: Optional[str] = None, title: Optional[str] = None) -> ChatSession:
        """Create new session"""
        return await self.session_manager.create_session(user_id, title)
    
    def update_retrieval_config(self, config: Dict[str, Any]) -> None:
        """Update retrieval configuration"""
        self.retrieval_config.update(config)
        
        # Update vectorstore retriever if needed
        if self.vectorstore:
            try:
                retriever = self.vectorstore.as_retriever(
                    search_kwargs={"k": self.retrieval_config["top_k"]}
                )
                # Recreate the chain with new retriever
                if self.chat_model:
                    self.retrieval_qa = ConversationalRetrievalChain.from_llm(
                        llm=self.chat_model,
                        retriever=retriever,
                        return_source_documents=True
                    )
            except Exception as e:
                print(f"Failed to update retrieval config: {e}")