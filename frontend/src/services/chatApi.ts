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
} from '../types/chat';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const chatApi = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach token to axios if present
const saved = localStorage.getItem('auth_token');
if (saved) {
  chatApi.defaults.headers.common['Authorization'] = `Bearer ${saved}`;
}

export const chatService = {
  async signup(username: string, password: string): Promise<{ user_id: string; username: string }> {
    const response = await chatApi.post('/auth/signup', { username, password });
    return response.data;
  },
  async login(username: string, password: string): Promise<{ access_token: string; token_type: string; user_id: string; username: string }> {
    const response = await chatApi.post('/auth/login', { username, password });
    const token = response.data?.access_token;
    if (token) {
      chatApi.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      localStorage.setItem('auth_token', token);
      localStorage.setItem('user_id', response.data.user_id);
      localStorage.setItem('username', response.data.username);
    }
    return response.data;
  },
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
      const token = localStorage.getItem('auth_token');
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