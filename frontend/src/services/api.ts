import axios from 'axios';
import {
  Document,
  DocumentUploadResponse,
  DocumentProcessingStatus,
  SearchRequest,
  SearchResponse,
  EmbedderConfig,
  VectorDBConfig,
  AppConfig,
  HealthStatus
} from '../types/api';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Upload API
export const uploadAPI = {
  uploadDocument: async (file: File): Promise<DocumentUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post<DocumentUploadResponse>('/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getDocumentStatus: async (documentId: string): Promise<DocumentProcessingStatus> => {
    const response = await api.get<DocumentProcessingStatus>(`/upload/status/${documentId}`);
    return response.data;
  },

  listDocuments: async (): Promise<{ documents: Document[]; total: number }> => {
    const response = await api.get('/upload/list');
    return response.data;
  },

  deleteDocument: async (documentId: string): Promise<{ message: string }> => {
    const response = await api.delete(`/upload/${documentId}`);
    return response.data;
  },

  searchDocuments: async (request: SearchRequest): Promise<SearchResponse> => {
    const response = await api.post<SearchResponse>('/upload/search', request);
    return response.data;
  },
};

// Configuration API
export const configAPI = {
  getCurrentConfig: async (): Promise<{ configured: boolean; config?: AppConfig }> => {
    const response = await api.get('/config/');
    return response.data;
  },

  updateEmbedderConfig: async (config: EmbedderConfig): Promise<{ message: string; embedder_info: any }> => {
    const response = await api.post('/config/embedder', config);
    return response.data;
  },

  updateVectorDBConfig: async (config: VectorDBConfig): Promise<{ message: string; stats: any }> => {
    const response = await api.post('/config/vector-db', config);
    return response.data;
  },

  updateCompleteConfig: async (config: AppConfig): Promise<{ message: string; embedder_info: any; vector_db_stats: any }> => {
    const response = await api.post('/config/complete', config);
    return response.data;
  },

  checkServiceHealth: async (): Promise<HealthStatus> => {
    const response = await api.get<HealthStatus>('/config/health');
    return response.data;
  },

  resetConfiguration: async (): Promise<{ message: string }> => {
    const response = await api.delete('/config/reset');
    return response.data;
  },
};

// General API
export const generalAPI = {
  getAppInfo: async (): Promise<any> => {
    const response = await api.get('/');
    return response.data;
  },

  healthCheck: async (): Promise<{ status: string; configured: boolean }> => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api; 