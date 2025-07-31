import os
import asyncio
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from app.models.document import DocumentType, DocumentUploadResponse, DocumentProcessingStatus
from app.models.search import SearchRequest, SearchResponse
from app.services.document_service import document_service
from app.config.settings import settings


router = APIRouter(prefix="/upload", tags=["upload"])


def get_document_type(filename: str) -> DocumentType:
    """Determine document type from filename"""
    extension = filename.lower().split('.')[-1]
    type_mapping = {
        'pdf': DocumentType.PDF,
        'docx': DocumentType.DOCX,
        'txt': DocumentType.TXT,
        'html': DocumentType.HTML,
        'md': DocumentType.MARKDOWN,
        'markdown': DocumentType.MARKDOWN
    }
    
    if extension not in type_mapping:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {extension}")
    
    return type_mapping[extension]


async def process_document_background(document_id: str, file_content: bytes):
    """Background task for processing documents"""
    try:
        await document_service.process_and_embed_document(document_id, file_content)
    except Exception as e:
        print(f"Error processing document {document_id}: {e}")


@router.post("/", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Upload and process a document"""
    try:
        # Validate file size
        file_content = await file.read()
        if len(file_content) > settings.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {settings.max_file_size} bytes"
            )
        
        # Determine file type
        file_type = get_document_type(file.filename)
        
        # Create document record
        document = await document_service.create_document(file.filename, file_type)
        
        # Start background processing
        background_tasks.add_task(process_document_background, document.id, file_content)
        
        return DocumentUploadResponse(
            document_id=document.id,
            status=document.status,
            message=f"Document '{file.filename}' uploaded successfully. Processing started."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")


@router.get("/status/{document_id}", response_model=DocumentProcessingStatus)
async def get_document_status(document_id: str):
    """Get document processing status"""
    try:
        status = document_service.get_document_status(document_id)
        if not status:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document status: {str(e)}")


@router.get("/list")
async def list_documents():
    """List all documents"""
    try:
        documents = document_service.list_documents()
        return {
            "documents": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "file_type": doc.file_type,
                    "status": doc.status,
                    "created_at": doc.created_at,
                    "processed_at": doc.processed_at,
                    "chunks_count": len(doc.chunks),
                    "error_message": doc.error_message
                }
                for doc in documents
            ],
            "total": len(documents)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and its vectors"""
    try:
        success = await document_service.delete_document(document_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"message": f"Document {document_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """Search for similar documents"""
    try:
        response = await document_service.search_documents(request)
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search documents: {str(e)}") 