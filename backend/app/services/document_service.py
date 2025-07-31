import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.models.document import Document, DocumentStatus, DocumentType, DocumentProcessingStatus
from app.models.search import SearchRequest, SearchResponse, SearchResult
from app.core.document_processor.langchain_processor import LangChainDocumentProcessor
from app.core.embedders.base import BaseEmbedder
from app.core.vector_db.base import BaseVectorDBClient
from app.config.settings import config_manager


class DocumentService:
    """Service for managing document processing and embedding operations"""
    
    def __init__(self):
        self.documents: Dict[str, Document] = {}
        self.document_processor = None
        self.embedder: Optional[BaseEmbedder] = None
        self.vector_db: Optional[BaseVectorDBClient] = None
        
    def _initialize_processor(self):
        """Initialize document processor with current settings"""
        config = config_manager.get_current_config()
        if config:
            self.document_processor = LangChainDocumentProcessor(
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap
            )
        else:
            self.document_processor = LangChainDocumentProcessor()
    
    async def create_document(self, filename: str, file_type: DocumentType) -> Document:
        """Create a new document record"""
        document_id = str(uuid.uuid4())
        document = Document(
            id=document_id,
            filename=filename,
            file_type=file_type,
            status=DocumentStatus.UPLOADED
        )
        self.documents[document_id] = document
        return document
    
    async def process_document(self, document_id: str, file_content: bytes) -> bool:
        """Process a document: extract text, clean, and split into chunks"""
        try:
            document = self.documents.get(document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Update status to processing
            document.status = DocumentStatus.PROCESSING
            
            # Initialize processor if needed
            if not self.document_processor:
                self._initialize_processor()
            
            # Process the document
            processed_document = await self.document_processor.process_document(document, file_content)
            
            # Update document
            self.documents[document_id] = processed_document
            processed_document.status = DocumentStatus.PROCESSED
            processed_document.processed_at = datetime.utcnow()
            
            return True
            
        except Exception as e:
            # Update status to error
            if document_id in self.documents:
                self.documents[document_id].status = DocumentStatus.ERROR
                self.documents[document_id].error_message = str(e)
            raise e
    
    async def embed_document(self, document_id: str) -> bool:
        """Generate embeddings for document chunks"""
        try:
            document = self.documents.get(document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            if not self.embedder:
                raise ValueError("Embedder not configured")
            
            # Extract text content from chunks
            texts = [chunk.content for chunk in document.chunks]
            if not texts:
                raise ValueError("No chunks to embed")
            
            # Generate embeddings
            embeddings = await self.embedder.embed_texts(texts)
            
            # Update chunks with embeddings
            for i, chunk in enumerate(document.chunks):
                if i < len(embeddings):
                    chunk.embedding = embeddings[i]
            
            document.status = DocumentStatus.EMBEDDED
            return True
            
        except Exception as e:
            # Update status to error
            if document_id in self.documents:
                self.documents[document_id].status = DocumentStatus.ERROR
                self.documents[document_id].error_message = str(e)
            raise e
    
    async def store_vectors(self, document_id: str) -> bool:
        """Store document chunk vectors in vector database"""
        try:
            document = self.documents.get(document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            if not self.vector_db:
                raise ValueError("Vector database not configured")
            
            # Filter chunks that have embeddings
            embedded_chunks = [chunk for chunk in document.chunks if chunk.embedding]
            if not embedded_chunks:
                raise ValueError("No embedded chunks to store")
            
            # Store vectors in database
            success = await self.vector_db.batch_upsert_vectors(embedded_chunks)
            if not success:
                raise RuntimeError("Failed to store vectors")
            
            return True
            
        except Exception as e:
            # Update status to error
            if document_id in self.documents:
                self.documents[document_id].status = DocumentStatus.ERROR
                self.documents[document_id].error_message = str(e)
            raise e
    
    async def process_and_embed_document(self, document_id: str, file_content: bytes) -> bool:
        """Complete document processing pipeline"""
        try:
            # Process document
            await self.process_document(document_id, file_content)
            
            # Generate embeddings
            await self.embed_document(document_id)
            
            # Store vectors
            await self.store_vectors(document_id)
            
            return True
            
        except Exception as e:
            raise e
    
    async def search_documents(self, request: SearchRequest) -> SearchResponse:
        """Search for similar documents"""
        start_time = asyncio.get_event_loop().time()
        
        if not self.embedder:
            raise ValueError("Embedder not configured")
        
        if not self.vector_db:
            raise ValueError("Vector database not configured")
        
        try:
            # Generate query embedding
            query_embedding = await self.embedder.embed_text(request.query)
            
            # Search vector database
            results = await self.vector_db.search_vectors(
                query_vector=query_embedding,
                top_k=request.top_k,
                threshold=request.threshold,
                filter_metadata=request.filter_metadata
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return SearchResponse(
                query=request.query,
                results=results,
                total_results=len(results),
                execution_time=execution_time
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to search documents: {str(e)}")
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """Get document by ID"""
        return self.documents.get(document_id)
    
    def get_document_status(self, document_id: str) -> Optional[DocumentProcessingStatus]:
        """Get document processing status"""
        document = self.documents.get(document_id)
        if not document:
            return None
        
        embedded_count = sum(1 for chunk in document.chunks if chunk.embedding)
        progress = 0.0
        
        if document.status == DocumentStatus.UPLOADED:
            progress = 0.0
        elif document.status == DocumentStatus.PROCESSING:
            progress = 25.0
        elif document.status == DocumentStatus.PROCESSED:
            progress = 50.0
        elif document.status == DocumentStatus.EMBEDDED:
            progress = 100.0
        elif document.status == DocumentStatus.ERROR:
            progress = 0.0
        
        return DocumentProcessingStatus(
            document_id=document_id,
            status=document.status,
            chunks_count=len(document.chunks),
            embedded_count=embedded_count,
            error_message=document.error_message,
            progress_percentage=progress
        )
    
    def list_documents(self) -> List[Document]:
        """List all documents"""
        return list(self.documents.values())
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete document and its vectors"""
        try:
            document = self.documents.get(document_id)
            if not document:
                return False
            
            # Delete vectors from vector database if configured
            if self.vector_db and document.chunks:
                chunk_ids = [chunk.id for chunk in document.chunks]
                await self.vector_db.delete_vectors(chunk_ids)
            
            # Remove from memory
            del self.documents[document_id]
            return True
            
        except Exception as e:
            raise RuntimeError(f"Failed to delete document: {str(e)}")
    
    def set_embedder(self, embedder: BaseEmbedder):
        """Set the embedder instance"""
        self.embedder = embedder
    
    def set_vector_db(self, vector_db: BaseVectorDBClient):
        """Set the vector database instance"""
        self.vector_db = vector_db


# Global document service instance
document_service = DocumentService() 