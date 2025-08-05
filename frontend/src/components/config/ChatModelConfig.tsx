/**
 * Chat model configuration component
 */

import React, { useState, useEffect } from 'react';
import { Save, AlertCircle, CheckCircle, MessageSquare, Settings, Trash2 } from 'lucide-react';
import { ChatModelConfig, ChatModelType } from '../../types/chat';
import { chatService } from '../../services/chatApi';

interface ChatModelConfigProps {
  onConfigUpdate?: () => void;
}

const ChatModelConfigComponent: React.FC<ChatModelConfigProps> = ({ onConfigUpdate }) => {
  const [config, setConfig] = useState<ChatModelConfig>({
    type: 'openai',
    openai: {
      api_key: '',
      model: 'gpt-3.5-turbo',
      temperature: 0.7,
      max_tokens: 1000,
      top_p: 1.0,
      frequency_penalty: 0.0,
      presence_penalty: 0.0,
    },
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isConfigured, setIsConfigured] = useState(false);

  useEffect(() => {
    loadCurrentConfig();
  }, []);

  const loadCurrentConfig = async () => {
    setIsLoading(true);
    try {
      const response = await chatService.getChatModelConfig();
      if (response.configured && response.config) {
        setConfig(response.config);
        setIsConfigured(true);
      }
    } catch (error) {
      console.error('Failed to load chat model config:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTypeChange = (type: ChatModelType) => {
    const newConfig: ChatModelConfig = {
      type,
      openai: type === 'openai' ? {
        api_key: '',
        model: 'gpt-3.5-turbo',
        temperature: 0.7,
        max_tokens: 1000,
        top_p: 1.0,
        frequency_penalty: 0.0,
        presence_penalty: 0.0,
      } : undefined,
      gemini: type === 'gemini' ? {
        api_key: '',
        model: 'gemini-2.0-flash',
        temperature: 0.7,
        max_tokens: 1000,
        top_p: 1.0,
        top_k: 40,
      } : undefined,
      local: type === 'local' ? {
        provider: 'ollama',
        model: 'llama2',
        temperature: 0.7,
        max_tokens: 1000,
        top_p: 1.0,
        top_k: 40,
        ollama_url: 'http://localhost:11434',
        trust_remote_code: true,
      } : undefined,
    };
    setConfig(newConfig);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setMessage(null);

    try {
      const response = await chatService.updateChatModelConfig(config);
      setMessage({ type: 'success', text: response.message });
      setIsConfigured(true);
      if (onConfigUpdate) {
        onConfigUpdate();
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update configuration';
      setMessage({ type: 'error', text: errorMessage });
    } finally {
      setIsSaving(false);
    }
  };

  const handleRemoveConfig = async () => {
    if (!window.confirm('Are you sure you want to remove the chat model configuration?')) {
      return;
    }

    setIsSaving(true);
    setMessage(null);

    try {
      const response = await chatService.removeChatModelConfig();
      setMessage({ type: 'success', text: response.message });
      setIsConfigured(false);
      // Reset to default config
      handleTypeChange('openai');
      if (onConfigUpdate) {
        onConfigUpdate();
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to remove configuration';
      setMessage({ type: 'error', text: errorMessage });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <MessageSquare className="w-8 h-8 text-blue-500" />
          <div>
            <h2 className="text-2xl font-bold text-gray-800">Chat Model Configuration</h2>
            <p className="text-gray-600">Configure your AI chat model for conversations</p>
          </div>
        </div>
        
        {isConfigured && (
          <button
            onClick={handleRemoveConfig}
            disabled={isSaving}
            className="flex items-center space-x-2 px-4 py-2 text-red-600 border border-red-300 rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50"
          >
            <Trash2 className="w-4 h-4" />
            <span>Remove Config</span>
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Model Type Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Chat Model Provider
          </label>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {([
              { value: 'openai', label: 'OpenAI', description: 'GPT-3.5/GPT-4 models' },
              { value: 'gemini', label: 'Google Gemini', description: 'Gemini Pro models' },
              { value: 'local', label: 'Local Models', description: 'Ollama/Transformers' },
            ] as const).map((option) => (
              <div
                key={option.value}
                className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                  config.type === option.value
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => handleTypeChange(option.value)}
              >
                <div className="font-medium text-gray-800">{option.label}</div>
                <div className="text-sm text-gray-600 mt-1">{option.description}</div>
              </div>
            ))}
          </div>
        </div>

        {/* OpenAI Configuration */}
        {config.type === 'openai' && config.openai && (
          <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
            <h3 className="font-medium text-gray-800">OpenAI Settings</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  API Key *
                </label>
                <input
                  type="password"
                  value={config.openai.api_key}
                  onChange={(e) => setConfig({
                    ...config,
                    openai: { ...config.openai!, api_key: e.target.value }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="sk-..."
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Model
                </label>
                <select
                  value={config.openai.model}
                  onChange={(e) => setConfig({
                    ...config,
                    openai: { ...config.openai!, model: e.target.value }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                  <option value="gpt-3.5-turbo-16k">GPT-3.5 Turbo 16K</option>
                  <option value="gpt-4">GPT-4</option>
                  <option value="gpt-4-turbo-preview">GPT-4 Turbo</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Organization (Optional)
                </label>
                <input
                  type="text"
                  value={config.openai.organization || ''}
                  onChange={(e) => setConfig({
                    ...config,
                    openai: { ...config.openai!, organization: e.target.value }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="org-..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Temperature ({config.openai.temperature})
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={config.openai.temperature}
                  onChange={(e) => setConfig({
                    ...config,
                    openai: { ...config.openai!, temperature: parseFloat(e.target.value) }
                  })}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Tokens
                </label>
                <input
                  type="number"
                  min="50"
                  max="4000"
                  value={config.openai.max_tokens}
                  onChange={(e) => setConfig({
                    ...config,
                    openai: { ...config.openai!, max_tokens: parseInt(e.target.value) }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Top P ({config.openai.top_p})
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={config.openai.top_p}
                  onChange={(e) => setConfig({
                    ...config,
                    openai: { ...config.openai!, top_p: parseFloat(e.target.value) }
                  })}
                  className="w-full"
                />
              </div>
            </div>
          </div>
        )}

        {/* Gemini Configuration */}
        {config.type === 'gemini' && config.gemini && (
          <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
            <h3 className="font-medium text-gray-800">Google Gemini Settings</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  API Key *
                </label>
                <input
                  type="password"
                  value={config.gemini.api_key}
                  onChange={(e) => setConfig({
                    ...config,
                    gemini: { ...config.gemini!, api_key: e.target.value }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="API key..."
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Model
                </label>
                <select
                  value={config.gemini.model}
                  onChange={(e) => setConfig({
                    ...config,
                    gemini: { ...config.gemini!, model: e.target.value }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                                  <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
                <option value="gemini-2.0-flash-exp">Gemini 2.0 Flash Experimental</option>
                <option value="gemini-pro">Gemini Pro (Legacy)</option>
                <option value="gemini-pro-vision">Gemini Pro Vision (Legacy)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Temperature ({config.gemini.temperature})
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={config.gemini.temperature}
                  onChange={(e) => setConfig({
                    ...config,
                    gemini: { ...config.gemini!, temperature: parseFloat(e.target.value) }
                  })}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Tokens
                </label>
                <input
                  type="number"
                  min="50"
                  max="8192"
                  value={config.gemini.max_tokens}
                  onChange={(e) => setConfig({
                    ...config,
                    gemini: { ...config.gemini!, max_tokens: parseInt(e.target.value) }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Top K
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={config.gemini.top_k}
                  onChange={(e) => setConfig({
                    ...config,
                    gemini: { ...config.gemini!, top_k: parseInt(e.target.value) }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* Local Configuration */}
        {config.type === 'local' && config.local && (
          <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
            <h3 className="font-medium text-gray-800">Local Model Settings</h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Provider
                </label>
                <select
                  value={config.local.provider}
                  onChange={(e) => setConfig({
                    ...config,
                    local: { ...config.local!, provider: e.target.value }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="ollama">Ollama</option>
                  <option value="transformers">Transformers</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Model Name
                </label>
                <input
                  type="text"
                  value={config.local.model}
                  onChange={(e) => setConfig({
                    ...config,
                    local: { ...config.local!, model: e.target.value }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="llama2, mistral, etc."
                />
              </div>

              {config.local.provider === 'ollama' && (
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Ollama Server URL
                  </label>
                  <input
                    type="url"
                    value={config.local.ollama_url}
                    onChange={(e) => setConfig({
                      ...config,
                      local: { ...config.local!, ollama_url: e.target.value }
                    })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="http://localhost:11434"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Temperature ({config.local.temperature})
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={config.local.temperature}
                  onChange={(e) => setConfig({
                    ...config,
                    local: { ...config.local!, temperature: parseFloat(e.target.value) }
                  })}
                  className="w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Tokens
                </label>
                <input
                  type="number"
                  min="50"
                  max="4000"
                  value={config.local.max_tokens}
                  onChange={(e) => setConfig({
                    ...config,
                    local: { ...config.local!, max_tokens: parseInt(e.target.value) }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* Message Display */}
        {message && (
          <div className={`p-4 rounded-lg flex items-center space-x-2 ${
            message.type === 'success' 
              ? 'bg-green-50 border border-green-200' 
              : 'bg-red-50 border border-red-200'
          }`}>
            {message.type === 'success' ? (
              <CheckCircle className="w-5 h-5 text-green-500" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-500" />
            )}
            <span className={message.type === 'success' ? 'text-green-800' : 'text-red-800'}>
              {message.text}
            </span>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isSaving}
            className="flex items-center space-x-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSaving ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            ) : (
              <Save className="w-4 h-4" />
            )}
            <span>{isSaving ? 'Saving...' : 'Save Configuration'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatModelConfigComponent;