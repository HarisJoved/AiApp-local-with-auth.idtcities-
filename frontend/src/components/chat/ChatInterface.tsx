/**
 * Main chat interface component
 */

import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, Plus, History, AlertCircle, CheckCircle, Settings } from 'lucide-react';
import ChatMessageComponent from './ChatMessage';
import ChatInput, { ChatInputOptions } from './ChatInput';
import SessionList from './SessionList';
import { ChatMessage, ConversationInfo, ChatResponse } from '../../types/chat';
import { chatService } from '../../services/chatApi';

interface ChatInterfaceProps {
  className?: string;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ className = '' }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<ConversationInfo[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [userId, setUserId] = useState<string>(() => {
    const authed = localStorage.getItem('user_id');
    if (authed) return authed;
    const existing = localStorage.getItem('demo_user_id');
    if (existing) return existing;
    const generated = 'user-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem('demo_user_id', generated);
    return generated;
  });
  // topicId removed in conversation model
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [showSessions, setShowSessions] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendConnected, setBackendConnected] = useState<boolean>(true);
  const [serviceHealth, setServiceHealth] = useState<{
    status: string;
    missing_components?: string[];
    chat_model?: string;
    embedder?: string;
    vector_db?: string;
    error?: string;
  } | null>(null);
  const [showDebug, setShowDebug] = useState<boolean>(false);
  const [lastDebug, setLastDebug] = useState<any>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamingMessageRef = useRef<string>('');

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load service health on mount
  useEffect(() => {
    loadServiceHealth();
    loadSessions();
  }, []);

  const loadServiceHealth = async () => {
    try {
      const health = await chatService.checkHealth();
      setServiceHealth(health);
      setBackendConnected(true);
      setError(null);
    } catch (error: any) {
      console.error('Failed to check service health:', error);
      setBackendConnected(false);
      setServiceHealth(null);
      
      // Check if it's a network/CORS error
      if (error.code === 'ERR_NETWORK' || error.message?.includes('CORS') || error.message?.includes('Network Error')) {
        setError('Backend server is not running or not accessible. Please start the backend server on http://localhost:8000');
      } else {
        setError('Failed to connect to chat service');
      }
    }
  };

  const loadSessions = async () => {
    try {
      const response = await chatService.listConversations(userId);
      setSessions(response.conversations);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    }
  };

  const createNewSession = async () => {
    try {
      const session = await chatService.createConversation({ user_id: userId });
      setCurrentSessionId(session.conversation_id);
      setMessages([]);
      await loadSessions();
      setShowSessions(false);
    } catch (error) {
      setError('Failed to create new session');
      console.error('Failed to create session:', error);
    }
  };

  const loadSession = async (sessionId: string) => {
    try {
      const session = await chatService.getConversation(sessionId);
      setCurrentSessionId(sessionId);
      setMessages(session.messages);
      setShowSessions(false);
    } catch (error) {
      setError('Failed to load session');
      console.error('Failed to load session:', error);
    }
  };

  const deleteSession = async (sessionId: string) => {
    try {
      await chatService.deleteConversation(sessionId);
      await loadSessions();
      if (currentSessionId === sessionId) {
        setCurrentSessionId(null);
        setMessages([]);
      }
    } catch (error) {
      setError('Failed to delete session');
      console.error('Failed to delete session:', error);
    }
  };

  const sendMessage = async (content: string, options: ChatInputOptions) => {
    if (!content.trim()) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setError(null);

    try {
      if (options.stream) {
        setIsStreaming(true);
        streamingMessageRef.current = '';

        // Add placeholder assistant message
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: '',
          timestamp: new Date().toISOString(),
        };
        setMessages(prev => [...prev, assistantMessage]);

        // Ensure we have a conversation_id for streaming so history threads correctly
        let sessionIdToUse = currentSessionId;
        if (!sessionIdToUse) {
          try {
            const newSession = await chatService.createConversation({ user_id: userId });
            sessionIdToUse = newSession.conversation_id;
            setCurrentSessionId(sessionIdToUse);
            } catch (e) {
            setIsStreaming(false);
            setError('Failed to create session');
            // remove placeholder assistant message
            setMessages(prev => prev.slice(0, -1));
            return;
          }
        }

        await chatService.streamMessage(
          {
            message: content.trim(),
            conversation_id: sessionIdToUse,
            user_id: userId,
            use_rag: options.useRAG,
            stream: true,
            temperature: options.temperature,
            max_tokens: options.maxTokens,
            token_limit: options.tokenLimit,
            summarize_target_ratio: options.summarizeTargetRatio,
          },
          // On chunk received
          (chunk: string) => {
            streamingMessageRef.current += chunk;
            setMessages(prev => {
              const newMessages = [...prev];
              if (newMessages.length > 0 && newMessages[newMessages.length - 1].role === 'assistant') {
                newMessages[newMessages.length - 1] = {
                  ...newMessages[newMessages.length - 1],
                  content: streamingMessageRef.current,
                };
              }
              return newMessages;
            });
          },
          // On complete
          () => {
            setIsStreaming(false);
            streamingMessageRef.current = '';
            loadSessions(); // Refresh sessions to update message counts
          },
          // On error
          (error: Error) => {
            setIsStreaming(false);
            setError(`Streaming error: ${error.message}`);
            // Remove the placeholder message
            setMessages(prev => prev.slice(0, -1));
          }
        );
      } else {
        setIsLoading(true);

        const response: ChatResponse = await chatService.sendMessage({
          message: content.trim(),
          conversation_id: currentSessionId || undefined,
          user_id: userId,
          use_rag: options.useRAG,
          temperature: options.temperature,
          max_tokens: options.maxTokens,
          token_limit: options.tokenLimit,
          summarize_target_ratio: options.summarizeTargetRatio,
        });

        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: response.message,
          timestamp: new Date().toISOString(),
        };

        setMessages(prev => [...prev, assistantMessage]);
        setLastDebug(response.debug || null);

        // Update current session ID if it was created
        if (!currentSessionId && response.conversation_id) {
          setCurrentSessionId(response.conversation_id);
        }

        await loadSessions(); // Refresh sessions
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to send message';
      setError(errorMessage);
      console.error('Failed to send message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const isServiceReady = serviceHealth?.status === 'ready';
  const hasMissingComponents = serviceHealth?.missing_components && serviceHealth.missing_components.length > 0;

  return (
    <div className={`flex h-full ${className}`}>
      {/* Session sidebar */}
      {showSessions && (
        <div className="w-80 border-r bg-gray-50 flex flex-col">
          <div className="p-4 border-b bg-white">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-gray-800">Chat Sessions</h2>
              <button
                onClick={() => setShowSessions(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                ×
              </button>
            </div>
          </div>
          <SessionList
            sessions={sessions}
            currentSessionId={currentSessionId}
            onSelectSession={loadSession}
            onDeleteSession={deleteSession}
            onNewSession={createNewSession}
          />
        </div>
      )}

      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b bg-white p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setShowSessions(!showSessions)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                title="Show sessions"
              >
                <History className="w-5 h-5 text-gray-600" />
              </button>
              
              <div className="flex items-center space-x-2">
                <MessageSquare className="w-6 h-6 text-blue-500" />
                <h1 className="text-xl font-semibold text-gray-800">
                  Document Chat Assistant
                </h1>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {/* Service status */}
              <div className="flex items-center space-x-1">
                {isServiceReady ? (
                  <>
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span className="text-sm text-green-600">Ready</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-4 h-4 text-yellow-500" />
                    <span className="text-sm text-yellow-600">Setup needed</span>
                  </>
                )}
              </div>

              <button
                onClick={createNewSession}
                className="flex items-center space-x-2 px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                title="New chat"
              >
                <Plus className="w-4 h-4" />
                <span>New Chat</span>
              </button>
              <button
                onClick={() => setShowDebug(v => !v)}
                className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors ${showDebug ? 'bg-gray-700 text-white' : 'bg-gray-200 text-gray-800 hover:bg-gray-300'}`}
                title="Toggle debug"
              >
                <Settings className="w-4 h-4" />
                <span>{showDebug ? 'Hide Debug' : 'Show Debug'}</span>
              </button>
            </div>
          </div>

          {/* Service health info */}
          {serviceHealth && !isServiceReady && (
            <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="flex items-center">
                <AlertCircle className="w-4 h-4 text-yellow-600 mr-2" />
                <span className="text-sm text-yellow-800">
                  {hasMissingComponents ? (
                    <>Missing components: {serviceHealth.missing_components!.join(', ')}</>
                  ) : serviceHealth.error ? (
                    <>Error: {serviceHealth.error}</>
                  ) : (
                    'Service not ready'
                  )}
                </span>
              </div>
              <div className="mt-1 text-xs text-yellow-700">
                Please configure the missing components in the Settings tab.
              </div>
            </div>
          )}
        </div>

        {/* Messages area */}
        <div className={`flex-1 overflow-y-auto bg-gray-50 ${showDebug ? 'grid grid-cols-2 gap-4' : ''}`}>
          <div className={`${showDebug ? 'px-4 py-6' : 'max-w-4xl mx-auto px-4 py-6' }`}>
            {!backendConnected ? (
              <div className="text-center py-12">
                <AlertCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-red-600 mb-2">
                  Backend Server Not Available
                </h3>
                <p className="text-gray-600 mb-4">
                  Unable to connect to the backend server. Please make sure:
                </p>
                <ul className="text-left text-sm text-gray-600 max-w-md mx-auto space-y-2 mb-6">
                  <li>• Backend server is running on <code className="bg-gray-200 px-1 rounded">http://localhost:8000</code></li>
                  <li>• CORS is properly configured</li>
                  <li>• No firewall is blocking the connection</li>
                </ul>
                <button
                  onClick={loadServiceHealth}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                >
                  Retry Connection
                </button>
              </div>
            ) : messages.length === 0 ? (
              <div className="text-center py-12">
                <MessageSquare className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-600 mb-2">
                  Start a conversation
                </h3>
                <p className="text-gray-500 mb-6">
                  Ask questions about your uploaded documents or have a general conversation.
                </p>
                {serviceHealth && (
                  <div className="text-sm text-gray-600 space-y-1">
                    <div>Chat Model: {serviceHealth.chat_model || 'Not configured'}</div>
                    <div>Embedder: {serviceHealth.embedder || 'Not configured'}</div>
                    <div>Vector DB: {serviceHealth.vector_db || 'Not configured'}</div>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-6">
                {messages.map((message, index) => (
                  <ChatMessageComponent
                    key={index}
                    message={message}
                    isStreaming={isStreaming && index === messages.length - 1}
                  />
                ))}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {showDebug && (
            <div className="px-4 py-6 border-l bg-white">
              <h3 className="text-md font-semibold text-gray-800 mb-3">Debug View</h3>
              {!lastDebug ? (
                <div className="text-sm text-gray-500">Send a message to see debug info.</div>
              ) : (
                <div className="space-y-4 text-sm">
                  {lastDebug.base_prompt && (
                    <div>
                      <div className="text-gray-700 font-medium mb-1">Base Prompt</div>
                      <div className="whitespace-pre-wrap bg-gray-50 border rounded p-2">{lastDebug.base_prompt}</div>
                    </div>
                  )}
                  {lastDebug.system_prompt && (
                    <div>
                      <div className="text-gray-700 font-medium mb-1">User Defined Prompt</div>
                      <div className="whitespace-pre-wrap bg-gray-50 border rounded p-2">{lastDebug.system_prompt}</div>
                    </div>
                  )}
                  {Array.isArray(lastDebug.used_chat_history) && lastDebug.used_chat_history.length > 0 && (
                    <div>
                      <div className="text-gray-700 font-medium mb-1">History</div>
                      <div className="space-y-2">
                        {lastDebug.used_chat_history
                          .filter((h: any) => h.type !== 'SystemMessage')
                          .map((h: any, idx: number) => (
                            <div key={idx} className="bg-gray-50 border rounded p-2">
                              <div className="text-xs text-gray-500 mb-1">{h.type}</div>
                              <div className="whitespace-pre-wrap">{h.content}</div>
                            </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {Array.isArray(lastDebug.summaries) && lastDebug.summaries.length > 0 && (
                    <div>
                      <div className="text-gray-700 font-medium mb-1">Summaries</div>
                      <ul className="list-disc ml-5 space-y-1">
                        {lastDebug.summaries.map((s: string, idx: number) => (
                          <li key={idx} className="whitespace-pre-wrap">{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {lastDebug.question && (
                    <div>
                      <div className="text-gray-700 font-medium mb-1">Question</div>
                      <div className="whitespace-pre-wrap bg-gray-50 border rounded p-2">{lastDebug.question}</div>
                    </div>
                  )}
                  {Array.isArray(lastDebug.context) && lastDebug.context.length > 0 && (
                    <div>
                      <div className="text-gray-700 font-medium mb-1">Context Chunks ({lastDebug.context.length})</div>
                      <div className="space-y-2">
                        {lastDebug.context.map((c: any, idx: number) => (
                          <div key={idx} className="bg-gray-50 border rounded p-2">
                            <div className="text-xs text-gray-500 mb-1">Score: {typeof c.score === 'number' ? c.score.toFixed(3) : c.score}</div>
                            <div className="whitespace-pre-wrap">{c.content}</div>
                            {c.metadata && Object.keys(c.metadata).length > 0 && (
                              <details className="mt-1">
                                <summary className="cursor-pointer text-xs text-gray-600">Metadata</summary>
                                <pre className="text-xs bg-white border rounded p-2 overflow-auto">{JSON.stringify(c.metadata, null, 2)}</pre>
                              </details>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {lastDebug.timings && (
                    <div>
                      <div className="text-gray-700 font-medium mb-1">Timings</div>
                      <pre className="text-xs bg-gray-50 border rounded p-2">{JSON.stringify(lastDebug.timings, null, 2)}</pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Error display */}
        {error && (
          <div className="mx-4 mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center">
              <AlertCircle className="w-4 h-4 text-red-500 mr-2" />
              <span className="text-sm text-red-800">{error}</span>
              <button
                onClick={() => setError(null)}
                className="ml-auto text-red-500 hover:text-red-700"
              >
                ×
              </button>
            </div>
          </div>
        )}

        {/* Chat input */}
        <ChatInput
          onSendMessage={sendMessage}
          disabled={!isServiceReady || !backendConnected}
          isLoading={isLoading || isStreaming}
          placeholder={
            !backendConnected
              ? "Backend server not available..."
              : isServiceReady
              ? "Ask me anything about your documents..."
              : "Please configure chat model first..."
          }
        />
      </div>
    </div>
  );
};

export default ChatInterface; 