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

// Import Keycloak service for token management
let keycloakService: any = null;

// Lazy import to avoid circular dependencies
const getKeycloakService = async () => {
  if (!keycloakService) {
    const module = await import('./keycloakService');
    keycloakService = module.keycloakService;
  }
  return keycloakService;
};

// Request interceptor to attach Keycloak token
api.interceptors.request.use(async (config) => {
  try {
    const service = await getKeycloakService();
    const token = service.getToken();
    const isAuthenticated = service.isAuthenticated();
    
    console.log('API Request Debug:', {
      url: config.url,
      isAuthenticated,
      hasToken: !!token,
      tokenLength: token?.length || 0
    });
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log('Authorization header added to request');
    } else {
      delete config.headers.Authorization;
      console.warn('No token available for request');
    }
  } catch (error) {
    console.warn('Failed to get Keycloak token:', error);
    delete config.headers.Authorization;
  }
  
  return config;
});

// Response interceptor to handle token expiration
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // If we get a 401 and haven't already tried to refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const service = await getKeycloakService();
        const refreshed = await service.updateToken();
        
        if (refreshed) {
          const token = service.getToken();
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        console.error('Token refresh failed:', refreshError);
        // Redirect to login will be handled by Keycloak context
      }
    }
    
    return Promise.reject(error);
  }
);

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