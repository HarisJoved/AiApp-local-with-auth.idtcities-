from abc import ABC, abstractmethod
from typing import List, Dict, Any, IO
from pathlib import Path

from app.models.document import Document, DocumentChunk, DocumentType


class BaseDocumentProcessor(ABC):
    """Abstract base class for document processors"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    @abstractmethod
    async def load_document(self, file_path: Path, file_type: DocumentType) -> str:
        """Load and extract text content from a document"""
        pass
    
    @abstractmethod
    def clean_text(self, text: str) -> str:
        """Clean and preprocess the extracted text"""
        pass
    
    @abstractmethod
    def split_text(self, text: str, metadata: Dict[str, Any] = None) -> List[DocumentChunk]:
        """Split text into chunks with metadata"""
        pass
    
    async def process_document(self, document: Document, file_content: bytes) -> Document:
        """Process a complete document: load, clean, and split"""
        import tempfile
        import os
        
        try:
            # Create a temporary file with proper extension
            file_extension = f".{document.file_type.value}"
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_file.write(file_content)
                temp_path = Path(temp_file.name)
            
            # Load document content
            text_content = await self.load_document(temp_path, document.file_type)
            
            # Clean text
            cleaned_text = self.clean_text(text_content)
            
            # Create document metadata
            metadata = {
                "filename": document.filename,
                "file_type": document.file_type.value,
                "original_length": len(text_content),
                "cleaned_length": len(cleaned_text)
            }
            
            # Split into chunks
            chunks = self.split_text(cleaned_text, metadata)
            
            # Update document
            document.content = cleaned_text
            document.chunks = chunks
            document.metadata = metadata
            
            return document
            
        except Exception as e:
            raise e
        finally:
            # Clean up temporary file
            if 'temp_path' in locals() and temp_path.exists():
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass  # Ignore cleanup errors 