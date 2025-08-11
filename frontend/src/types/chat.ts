/**
 * TypeScript interfaces for chat functionality
 */

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  user_id?: string;
  topic_id?: string;
  use_rag?: boolean;
  stream?: boolean;
  temperature?: number;
  max_tokens?: number;
}

export interface RetrievedChunk {
  content: string;
  score: number;
  metadata: Record<string, any>;
}

export interface ChatResponse {
  message: string;
  session_id: string;
  model_info?: string;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  retrieved_chunks: RetrievedChunk[];
  retrieval_time: number;
  generation_time: number;
  total_time: number;
}

export interface SessionInfo {
  session_id: string;
  user_id?: string;
  title: string;
  created_at: string;
  last_activity: string;
  message_count: number;
}

export interface SessionListResponse {
  sessions: SessionInfo[];
  total: number;
}

export interface SessionCreateRequest {
  user_id?: string;
  title?: string;
}

export interface SessionHistoryResponse {
  session_id: string;
  messages: ChatMessage[];
  title: string;
  created_at: string;
  last_activity: string;
}

export interface TopicInfo {
  topic_id: string;
  title: string;
  created_at: string;
  session_count: number;
}

export interface TopicListResponse {
  topics: TopicInfo[];
  total: number;
}

export interface TopicCreateRequest {
  user_id: string;
  title?: string;
}

export interface MessageRecord {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface SessionMessagesResponse {
  session_id: string;
  messages: MessageRecord[];
}

// Chat model configuration types
export type ChatModelType = 'openai' | 'gemini' | 'local';

export interface OpenAIChatConfig {
  api_key: string;
  model?: string;
  organization?: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
}

export interface GeminiChatConfig {
  api_key: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  top_k?: number;
}

export interface LocalChatConfig {
  provider?: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  top_k?: number;
  ollama_url?: string;
  trust_remote_code?: boolean;
}

export interface ChatModelConfig {
  type: ChatModelType;
  openai?: OpenAIChatConfig;
  gemini?: GeminiChatConfig;
  local?: LocalChatConfig;
}