"""
Pydantic models for chat API requests and responses.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """Chat message from API request"""
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat API request (conversation-based)"""
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    user_id: Optional[str] = Field(None, description="User ID")
    use_rag: bool = Field(default=True, description="Use document retrieval")
    stream: bool = Field(default=False, description="Stream response")
    temperature: Optional[float] = Field(None, description="Override model temperature")
    max_tokens: Optional[int] = Field(None, description="Override max tokens")
    token_limit: Optional[int] = Field(128_000, description="Max tokens to retain per conversation")
    summarize_target_ratio: Optional[float] = Field(0.8, description="Target ratio after summarization")


class RetrievedChunk(BaseModel):
    """Retrieved document chunk"""
    content: str = Field(..., description="Chunk content")
    score: float = Field(..., description="Similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")


class ChatResponse(BaseModel):
    """Chat API response"""
    message: str = Field(..., description="Assistant response")
    conversation_id: str = Field(..., description="Conversation ID")
    model_info: Optional[str] = Field(None, description="Model information")
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage")
    retrieved_chunks: List[RetrievedChunk] = Field(default_factory=list, description="Retrieved document chunks")
    retrieval_time: float = Field(default=0.0, description="Time spent on retrieval (seconds)")
    generation_time: float = Field(default=0.0, description="Time spent on generation (seconds)")
    total_time: float = Field(default=0.0, description="Total processing time (seconds)")
    debug: Optional[Dict[str, Any]] = Field(None, description="Debug information for UI")


class ConversationInfo(BaseModel):
    """Conversation information"""
    conversation_id: str = Field(..., description="Conversation ID")
    user_id: Optional[str] = Field(None, description="User ID")
    title: str = Field(..., description="Conversation title")
    created_at: str = Field(..., description="Creation timestamp")
    last_activity: str = Field(..., description="Last activity timestamp")
    message_count: int = Field(..., description="Number of messages in conversation")
    token_count_total: int = Field(default=0, description="Total token count")


class ConversationListResponse(BaseModel):
    """Response for listing conversations"""
    conversations: List[ConversationInfo] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total number of conversations")


class ConversationCreateRequest(BaseModel):
    """Request to create a new conversation"""
    user_id: Optional[str] = Field(None, description="User ID")
    title: Optional[str] = Field(None, description="Conversation title")
    token_limit: Optional[int] = Field(128_000, description="Max token budget")


class ConversationHistoryResponse(BaseModel):
    """Response for conversation history"""
    conversation_id: str = Field(..., description="Conversation ID")
    messages: List[ChatMessageRequest] = Field(..., description="Conversation messages")
    title: str = Field(..., description="Conversation title")
    created_at: str = Field(..., description="Creation timestamp")
    last_activity: str = Field(..., description="Last activity timestamp")


# ---------- RAG Prompts ----------

class RAGPromptCreate(BaseModel):
    name: str = Field(..., description="Prompt name")
    content: str = Field(..., description="Prompt template text")
    set_active: bool = Field(default=False, description="Set as active after creation")


class RAGPromptUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Prompt name")
    content: Optional[str] = Field(None, description="Prompt template text")


class RAGPromptInfo(BaseModel):
    prompt_id: str
    name: str
    content: str
    is_active: bool = False
    created_at: str
    updated_at: Optional[str] = None


class RAGPromptListResponse(BaseModel):
    prompts: List[RAGPromptInfo]


class RAGPromptActiveResponse(BaseModel):
    prompt: Optional[RAGPromptInfo] = None


class TopicInfo(BaseModel):
    topic_id: str
    title: str
    created_at: str
    session_count: int = 0


class TopicListResponse(BaseModel):
    topics: List[TopicInfo]
    total: int


class TopicCreateRequest(BaseModel):
    user_id: str
    title: str = Field(default="General")


class SessionCreateUnderTopicRequest(BaseModel):
    user_id: str
    topic_id: str
    title: Optional[str] = Field(default="New Chat")


class MessageRecord(BaseModel):
    role: str
    content: str
    timestamp: str


class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: List[MessageRecord]