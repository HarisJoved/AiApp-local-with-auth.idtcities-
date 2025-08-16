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
  conversation_id?: string;
  user_id?: string;
  use_rag?: boolean;
  stream?: boolean;
  temperature?: number;
  max_tokens?: number;
  token_limit?: number;
  summarize_target_ratio?: number;
}

export interface RetrievedChunk {
  content: string;
  score: number;
  metadata: Record<string, any>;
}

export interface ChatResponse {
  message: string;
  conversation_id: string;
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
  debug?: {
    system_prompt?: string;
    base_prompt?: string;
    retriever_top_k?: number;
    used_chat_history?: Array<{ type: string; content: string }>;
    summaries?: string[];
    question?: string;
    context?: RetrievedChunk[];
    timings?: {
      retrieval_time?: number;
      generation_time?: number;
      total_time?: number;
    };
  };
}

export interface ConversationInfo {
  conversation_id: string;
  user_id?: string;
  title: string;
  created_at: string;
  last_activity: string;
  message_count: number;
  token_count_total: number;
}

export interface ConversationListResponse {
  conversations: ConversationInfo[];
  total: number;
}

export interface ConversationCreateRequest {
  user_id?: string;
  title?: string;
  token_limit?: number;
}

export interface ConversationHistoryResponse {
  conversation_id: string;
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

// Deprecated: session-specific response is no longer used in conversation model

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

// RAG Prompt Types
export interface RAGPromptInfo {
  prompt_id: string;
  name: string;
  content: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface RAGPromptListResponse {
  prompts: RAGPromptInfo[];
}

export interface RAGPromptCreate {
  name: string;
  content: string;
  set_active?: boolean;
}

export interface RAGPromptUpdate {
  name?: string;
  content?: string;
}

export interface RAGPromptActiveResponse {
  prompt?: RAGPromptInfo | null;
}