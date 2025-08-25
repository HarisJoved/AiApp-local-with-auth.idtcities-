/**
 * API service for chat functionality
 */

import axios from 'axios';
import {
  ChatRequest,
  ChatResponse,
  ConversationInfo,
  ConversationListResponse,
  ConversationCreateRequest,
  ConversationHistoryResponse,
  ChatModelConfig,
  RAGPromptInfo,
  RAGPromptListResponse,
  RAGPromptCreate,
  RAGPromptUpdate,
  RAGPromptActiveResponse,
} from '../types/chat';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const chatApi = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
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
chatApi.interceptors.request.use(async (config) => {
  try {
    const service = await getKeycloakService();
    const token = service.getToken();
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      delete config.headers.Authorization;
    }
  } catch (error) {
    console.warn('Failed to get Keycloak token:', error);
    delete config.headers.Authorization;
  }
  
  return config;
});

export const chatService = {
  /**
   * Send a chat message
   */
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await chatApi.post('/chat/', request);
    return response.data;
  },

  /**
   * Stream a chat message (for real-time responses)
   */
  async streamMessage(
    request: ChatRequest,
    onChunk: (chunk: string) => void,
    onComplete: () => void,
    onError: (error: Error) => void
  ): Promise<void> {
    try {
      const streamRequest = { ...request, stream: true };
      const service = await getKeycloakService();
      const token = service.getToken();
      const response = await fetch(`${API_BASE_URL}/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(streamRequest),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const chunk = line.slice(6);
            if (chunk === '[DONE]') {
              onComplete();
              return;
            } else if (chunk.startsWith('Error: ')) {
              onError(new Error(chunk.slice(7)));
              return;
            } else {
              onChunk(chunk);
            }
          }
        }
      }

      onComplete();
    } catch (error) {
      onError(error instanceof Error ? error : new Error('Unknown error'));
    }
  },

  /**
   * Create a new chat session
   */
  async createConversation(request: ConversationCreateRequest): Promise<ConversationInfo> {
    const response = await chatApi.post('/chat/conversations', request);
    return response.data;
  },

  /**
   * List chat sessions
   */
  async listConversations(userId?: string): Promise<ConversationListResponse> {
    const params = userId ? { user_id: userId } : {};
    const response = await chatApi.get('/chat/conversations', { params });
    return response.data;
  },

  /**
   * Topics (Neo4j)
   */
  // Topic APIs removed in conversation-based model

  /**
   * Get session history
   */
  async getConversation(conversationId: string): Promise<ConversationHistoryResponse> {
    const response = await chatApi.get(`/chat/conversations/${conversationId}`);
    return response.data;
  },

  /**
   * Delete a session
   */
  async deleteConversation(conversationId: string): Promise<void> {
    await chatApi.delete(`/chat/conversations/${conversationId}`);
  },

  /**
   * Check chat service health
   */
  async checkHealth(): Promise<{
    status: string;
    missing_components: string[];
    chat_model?: string;
    embedder?: string;
    vector_db?: string;
  }> {
    const response = await chatApi.get('/chat/health');
    return response.data;
  },

  // RAG Prompts
  async listPrompts(): Promise<RAGPromptListResponse> {
    const response = await chatApi.get('/chat/prompts');
    return response.data;
  },
  async createPrompt(data: RAGPromptCreate): Promise<RAGPromptInfo> {
    const response = await chatApi.post('/chat/prompts', data);
    return response.data;
  },
  async updatePrompt(promptId: string, data: RAGPromptUpdate): Promise<RAGPromptInfo> {
    const response = await chatApi.patch(`/chat/prompts/${promptId}`, data);
    return response.data;
  },
  async deletePrompt(promptId: string): Promise<{ message: string }> {
    const response = await chatApi.delete(`/chat/prompts/${promptId}`);
    return response.data;
  },
  async activatePrompt(promptId: string): Promise<{ message: string }> {
    const response = await chatApi.post(`/chat/prompts/${promptId}/activate`);
    return response.data;
  },
  async getActivePrompt(): Promise<RAGPromptActiveResponse> {
    const response = await chatApi.get('/chat/prompts/active');
    return response.data;
  },

  /**
   * Update chat model configuration
   */
  async updateChatModelConfig(config: ChatModelConfig): Promise<{
    message: string;
    chat_model_info: string;
  }> {
    const response = await chatApi.post('/config/chat-model', config);
    return response.data;
  },

  /**
   * Get chat model configuration
   */
  async getChatModelConfig(): Promise<{
    configured: boolean;
    config?: ChatModelConfig;
    message?: string;
  }> {
    const response = await chatApi.get('/config/chat-model');
    return response.data;
  },

  /**
   * Remove chat model configuration
   */
  async removeChatModelConfig(): Promise<{ message: string }> {
    const response = await chatApi.delete('/config/chat-model');
    return response.data;
  },

  /**
   * Update RAG configuration
   */
  async updateRAGConfig(config: {
    top_k?: number;
    similarity_threshold?: number;
    max_context_length?: number;
  }): Promise<{
    message: string;
    config: {
      top_k: number;
      similarity_threshold: number;
      max_context_length: number;
    };
  }> {
    const params = new URLSearchParams();
    if (config.top_k !== undefined) params.append('top_k', config.top_k.toString());
    if (config.similarity_threshold !== undefined) params.append('similarity_threshold', config.similarity_threshold.toString());
    if (config.max_context_length !== undefined) params.append('max_context_length', config.max_context_length.toString());

    const response = await chatApi.post(`/config/rag?${params.toString()}`);
    return response.data;
  },
};

export default chatService;