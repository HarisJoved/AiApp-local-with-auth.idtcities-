// Document types
export type DocumentType = 'pdf' | 'docx' | 'txt' | 'html' | 'markdown';
export type DocumentStatus = 'uploaded' | 'processing' | 'processed' | 'embedded' | 'error';

export interface Document {
  id: string;
  filename: string;
  file_type: DocumentType;
  status: DocumentStatus;
  created_at: string;
  processed_at?: string;
  chunks_count: number;
  error_message?: string;
}

export interface DocumentProcessingStatus {
  document_id: string;
  status: DocumentStatus;
  chunks_count: number;
  embedded_count: number;
  error_message?: string;
  progress_percentage: number;
}

export interface DocumentUploadResponse {
  document_id: string;
  status: DocumentStatus;
  message: string;
}

// Configuration types
export type EmbedderType = 'openai' | 'huggingface';
export type VectorDBType = 'pinecone' | 'chromadb' | 'qdrant';

export interface OpenAIEmbedderConfig {
  api_key: string;
  model_name: string;
  organization?: string;
  timeout: number;
}

export interface HuggingFaceEmbedderConfig {
  model_name: string;
  device: string;
  trust_remote_code: boolean;
  cache_dir?: string;
}

export interface EmbedderConfig {
  type: EmbedderType;
  openai?: OpenAIEmbedderConfig;
  huggingface?: HuggingFaceEmbedderConfig;
}

export interface PineconeDBConfig {
  api_key: string;
  environment: string;
  index_name: string;
  dimension: number;
  metric: string;
}

export interface ChromaDBConfig {
  host: string;
  port: number;
  collection_name: string;
  persist_directory?: string;
}

export interface QdrantDBConfig {
  host: string;
  port: number;
  collection_name: string;
  api_key?: string;
  https: boolean;
}

export interface VectorDBConfig {
  type: VectorDBType;
  pinecone?: PineconeDBConfig;
  chromadb?: ChromaDBConfig;
  qdrant?: QdrantDBConfig;
}

export interface AppConfig {
  embedder: EmbedderConfig;
  vector_db: VectorDBConfig;
  max_file_size: number;
  chunk_size: number;
  chunk_overlap: number;
}

// Search types
export interface SearchRequest {
  query: string;
  top_k: number;
  threshold: number;
  filter_metadata?: Record<string, any>;
}

export interface SearchResult {
  chunk_id: string;
  document_id: string;
  content: string;
  score: number;
  metadata: Record<string, any>;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  execution_time: number;
}

// Health check types
export interface HealthStatus {
  configured: boolean;
  embedder: {
    healthy: boolean;
    info?: any;
    error?: string;
  };
  vector_db: {
    healthy: boolean;
    stats?: any;
    error?: string;
  };
} 