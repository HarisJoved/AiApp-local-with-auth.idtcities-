from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    top_k: int = Field(default=5, description="Number of results to return")
    threshold: float = Field(default=0.0, description="Minimum similarity threshold")
    filter_metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")


class SearchResult(BaseModel):
    chunk_id: str = Field(..., description="Chunk ID")
    document_id: str = Field(..., description="Source document ID")
    content: str = Field(..., description="Chunk content")
    score: float = Field(..., description="Similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")


class SearchResponse(BaseModel):
    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results found")
    execution_time: float = Field(..., description="Query execution time in seconds") 