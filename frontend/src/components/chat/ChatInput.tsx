/**
 * Chat input component for sending messages
 */

import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Settings, Database } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (message: string, options: ChatInputOptions) => void;
  disabled?: boolean;
  isLoading?: boolean;
  placeholder?: string;
}

export interface ChatInputOptions {
  useRAG: boolean;
  temperature?: number;
  maxTokens?: number;
  stream: boolean;
  tokenLimit?: number;
  summarizeTargetRatio?: number;
}

const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled = false,
  isLoading = false,
  placeholder = "Ask me anything about your documents...",
}) => {
  const [message, setMessage] = useState('');
  const [showOptions, setShowOptions] = useState(false);
  const [options, setOptions] = useState<ChatInputOptions>({
    useRAG: true,
    stream: false,
    temperature: 0.7,
    maxTokens: 1000,
    tokenLimit: 1200,
    summarizeTargetRatio: 0.8,
  });

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled && !isLoading) {
      onSendMessage(message.trim(), options);
      setMessage('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="border-t bg-white p-4">
      {/* Options panel */}
      {showOptions && (
        <div className="mb-4 p-4 bg-gray-50 rounded-lg space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-medium text-gray-800">Chat Options</h3>
            <button
              onClick={() => setShowOptions(false)}
              className="text-gray-500 hover:text-gray-700"
            >
              ×
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* RAG Toggle */}
            <div className="flex items-center">
              <input
                type="checkbox"
                id="useRAG"
                checked={options.useRAG}
                onChange={(e) => setOptions({ ...options, useRAG: e.target.checked })}
                className="mr-2"
              />
              <label htmlFor="useRAG" className="text-sm text-gray-700 flex items-center">
                <Database className="w-4 h-4 mr-1" />
                Use document context (RAG)
              </label>
            </div>

            {/* Streaming Toggle */}
            <div className="flex items-center">
              <input
                type="checkbox"
                id="stream"
                checked={options.stream}
                onChange={(e) => setOptions({ ...options, stream: e.target.checked })}
                className="mr-2"
              />
              <label htmlFor="stream" className="text-sm text-gray-700">
                Stream response
              </label>
            </div>

            {/* Temperature */}
            <div>
              <label htmlFor="temperature" className="block text-sm text-gray-700 mb-1">
                Temperature: {options.temperature}
              </label>
              <input
                type="range"
                id="temperature"
                min="0"
                max="2"
                step="0.1"
                value={options.temperature}
                onChange={(e) => setOptions({ ...options, temperature: parseFloat(e.target.value) })}
                className="w-full"
              />
            </div>

            {/* Max Tokens */}
            <div>
              <label htmlFor="maxTokens" className="block text-sm text-gray-700 mb-1">
                Max Tokens
              </label>
              <input
                type="number"
                id="maxTokens"
                min="50"
                max="4000"
                step="50"
                value={options.maxTokens}
                onChange={(e) => setOptions({ ...options, maxTokens: parseInt(e.target.value) })}
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              />
            </div>

            {/* Conversation Token Limit */}
            <div>
              <label htmlFor="tokenLimit" className="block text-sm text-gray-700 mb-1">
                Conversation Token Limit
              </label>
              <input
                type="number"
                id="tokenLimit"
                min="1000"
                max="512000"
                step="1000"
                value={options.tokenLimit}
                onChange={(e) => setOptions({ ...options, tokenLimit: parseInt(e.target.value) })}
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              />
            </div>

            {/* Summarize Target Ratio */}
            <div>
              <label htmlFor="summarizeTargetRatio" className="block text-sm text-gray-700 mb-1">
                Summarize Target Ratio
              </label>
              <input
                type="number"
                id="summarizeTargetRatio"
                min="0.5"
                max="0.95"
                step="0.01"
                value={options.summarizeTargetRatio}
                onChange={(e) => setOptions({ ...options, summarizeTargetRatio: parseFloat(e.target.value) })}
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              />
            </div>
          </div>
        </div>
      )}

      {/* Main input form */}
      <form onSubmit={handleSubmit} className="flex items-end space-x-2">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={placeholder}
            disabled={disabled || isLoading}
            rows={1}
            className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            style={{ minHeight: '48px', maxHeight: '120px' }}
          />
          
          {/* Character count */}
          {message.length > 0 && (
            <div className="absolute bottom-1 right-12 text-xs text-gray-400">
              {message.length}
            </div>
          )}
        </div>

        {/* Options button */}
        <button
          type="button"
          onClick={() => setShowOptions(!showOptions)}
          className={`p-3 rounded-lg border transition-colors ${
            showOptions
              ? 'bg-blue-50 border-blue-300 text-blue-600'
              : 'bg-gray-50 border-gray-300 text-gray-600 hover:bg-gray-100'
          }`}
          title="Chat options"
        >
          <Settings className="w-5 h-5" />
        </button>

        {/* Send button */}
        <button
          type="submit"
          disabled={!message.trim() || disabled || isLoading}
          className="p-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          title="Send message"
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </form>

      {/* Hints */}
      <div className="mt-2 text-xs text-gray-500 flex items-center justify-between">
        <span>Press Enter to send, Shift+Enter for new line</span>
        {options.useRAG && (
          <span className="flex items-center">
            <Database className="w-3 h-3 mr-1" />
            RAG enabled
          </span>
        )}
      </div>
    </div>
  );
};

export default ChatInput;