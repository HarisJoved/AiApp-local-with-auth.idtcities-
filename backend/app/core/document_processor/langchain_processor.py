import uuid
from typing import List, Dict, Any
from pathlib import Path

from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.models.document import Document, DocumentChunk, DocumentType
from .base import BaseDocumentProcessor


class LangChainDocumentProcessor(BaseDocumentProcessor):
    """Document processor using LangChain loaders and text splitters"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        super().__init__(chunk_size, chunk_overlap)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Map document types to loaders
        self.loader_map = {
            DocumentType.PDF: PyPDFLoader,
            DocumentType.DOCX: Docx2txtLoader,
            DocumentType.TXT: TextLoader,
            DocumentType.HTML: UnstructuredHTMLLoader,
            DocumentType.MARKDOWN: UnstructuredMarkdownLoader
        }
    
    async def load_document(self, file_path: Path, file_type: DocumentType) -> str:
        """Load document using appropriate LangChain loader"""
        loader_class = self.loader_map.get(file_type)
        if not loader_class:
            raise ValueError(f"Unsupported document type: {file_type}")
        
        try:
            loader = loader_class(str(file_path))
            documents = loader.load()
            
            # Combine all pages/sections into one text
            full_text = "\n\n".join([doc.page_content for doc in documents])
            return full_text
            
        except Exception as e:
            raise ValueError(f"Failed to load document: {str(e)}")
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Basic text cleaning
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove excessive whitespace
            line = ' '.join(line.split())
            
            # Skip empty lines and very short lines
            if len(line.strip()) < 3:
                continue
                
            cleaned_lines.append(line)
        
        # Join lines and normalize spaces
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Remove multiple consecutive newlines
        while '\n\n\n' in cleaned_text:
            cleaned_text = cleaned_text.replace('\n\n\n', '\n\n')
        
        return cleaned_text.strip()
    
    def split_text(self, text: str, metadata: Dict[str, Any] = None) -> List[DocumentChunk]:
        """Split text into chunks using LangChain text splitter"""
        if not text:
            return []
        
        if metadata is None:
            metadata = {}
        
        # Split text into chunks
        text_chunks = self.text_splitter.split_text(text)
        
        # Create DocumentChunk objects
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunk_metadata = {
                **metadata,
                "chunk_index": i,
                "chunk_length": len(chunk_text),
                "chunk_start": text.find(chunk_text) if chunk_text in text else -1
            }
            
            chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                content=chunk_text,
                metadata=chunk_metadata
            )
            chunks.append(chunk)
        
        return chunks 