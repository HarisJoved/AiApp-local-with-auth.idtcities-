/**
 * Individual chat message component
 */

import React from 'react';
import { User, Bot, Clock, Info } from 'lucide-react';
import { ChatMessage } from '../../types/chat';

interface ChatMessageProps {
  message: ChatMessage;
  isStreaming?: boolean;
  modelInfo?: string;
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  retrievalTime?: number;
  generationTime?: number;
  retrievedChunks?: number;
}

const ChatMessageComponent: React.FC<ChatMessageProps> = ({
  message,
  isStreaming = false,
  modelInfo,
  usage,
  retrievalTime,
  generationTime,
  retrievedChunks,
}) => {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <div className="flex justify-center my-4">
        <div className="bg-gray-100 text-gray-600 px-4 py-2 rounded-lg text-sm">
          <Info className="inline-block w-4 h-4 mr-2" />
          {message.content}
        </div>
      </div>
    );
  }

  const formatTime = (timestamp?: string) => {
    if (!timestamp) return '';
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      <div className={`max-w-[70%] ${isUser ? 'order-2' : 'order-1'}`}>
        {/* Message bubble */}
        <div
          className={`px-4 py-3 rounded-2xl ${
            isUser
              ? 'bg-blue-500 text-white rounded-br-md'
              : 'bg-gray-100 text-gray-800 rounded-bl-md'
          }`}
        >
          {/* Avatar and name */}
          <div className="flex items-center mb-2">
            <div
              className={`flex items-center justify-center w-6 h-6 rounded-full mr-2 ${
                isUser ? 'bg-blue-600' : 'bg-gray-300'
              }`}
            >
              {isUser ? (
                <User className="w-4 h-4 text-white" />
              ) : (
                <Bot className="w-4 h-4 text-gray-600" />
              )}
            </div>
            <span className={`text-sm font-medium ${isUser ? 'text-blue-100' : 'text-gray-600'}`}>
              {isUser ? 'You' : 'Assistant'}
            </span>
            {message.timestamp && (
              <span className={`text-xs ml-2 ${isUser ? 'text-blue-200' : 'text-gray-500'}`}>
                <Clock className="inline-block w-3 h-3 mr-1" />
                {formatTime(message.timestamp)}
              </span>
            )}
          </div>

          {/* Message content */}
          <div className={`prose max-w-none ${isUser ? 'prose-invert' : ''}`}>
            <div className="whitespace-pre-wrap break-words">
              {message.content}
              {isStreaming && <span className="animate-pulse">▊</span>}
            </div>
          </div>
        </div>

        {/* Message metadata (for assistant messages) */}
        {!isUser && (modelInfo || usage || retrievalTime !== undefined) && (
          <div className="mt-2 text-xs text-gray-500 space-y-1">
            {modelInfo && (
              <div className="flex items-center">
                <span className="font-medium">Model:</span>
                <span className="ml-1">{modelInfo}</span>
              </div>
            )}
            
            {retrievedChunks !== undefined && retrievedChunks > 0 && (
              <div className="flex items-center">
                <span className="font-medium">Retrieved chunks:</span>
                <span className="ml-1">{retrievedChunks}</span>
              </div>
            )}

            {(retrievalTime !== undefined || generationTime !== undefined) && (
              <div className="flex items-center space-x-4">
                {retrievalTime !== undefined && (
                  <span>
                    <span className="font-medium">Retrieval:</span> {retrievalTime.toFixed(2)}s
                  </span>
                )}
                {generationTime !== undefined && (
                  <span>
                    <span className="font-medium">Generation:</span> {generationTime.toFixed(2)}s
                  </span>
                )}
              </div>
            )}

            {usage && (
              <div className="flex items-center space-x-4">
                <span>
                  <span className="font-medium">Tokens:</span> {usage.total_tokens}
                </span>
                <span className="text-gray-400">
                  ({usage.prompt_tokens} + {usage.completion_tokens})
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessageComponent;