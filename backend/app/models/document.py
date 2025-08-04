from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"
    MARKDOWN = "markdown"
    PPTX = "pptx"
    XLSX = "xlsx"
    XLS = "xls"


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    EMBEDDED = "embedded"
    ERROR = "error"


class DocumentChunk(BaseModel):
    id: str = Field(..., description="Unique chunk ID")
    content: str = Field(..., description="Chunk text content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")
    
    
class Document(BaseModel):
    id: str = Field(..., description="Unique document ID")
    filename: str = Field(..., description="Original filename")
    file_type: DocumentType = Field(..., description="Document type")
    content: Optional[str] = Field(None, description="Full document content")
    chunks: List[DocumentChunk] = Field(default_factory=list, description="Document chunks")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    status: DocumentStatus = Field(default=DocumentStatus.UPLOADED, description="Processing status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")


class DocumentUploadRequest(BaseModel):
    filename: str = Field(..., description="Document filename")
    file_type: DocumentType = Field(..., description="Document type")


class DocumentUploadResponse(BaseModel):
    document_id: str = Field(..., description="Created document ID")
    status: DocumentStatus = Field(..., description="Document status")
    message: str = Field(..., description="Status message")


class DocumentProcessingStatus(BaseModel):
    document_id: str = Field(..., description="Document ID")
    status: DocumentStatus = Field(..., description="Current status")
    chunks_count: int = Field(default=0, description="Number of chunks created")
    embedded_count: int = Field(default=0, description="Number of chunks embedded")
    error_message: Optional[str] = Field(None, description="Error message if any")
    progress_percentage: float = Field(default=0.0, description="Processing progress percentage") 