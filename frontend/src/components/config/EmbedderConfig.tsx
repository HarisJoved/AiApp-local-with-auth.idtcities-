import React, { useState } from 'react';
import { EmbedderConfig as EmbedderConfigType, EmbedderType } from '../../types/api';
import { configAPI } from '../../services/api';

interface EmbedderConfigProps {
  initialConfig?: EmbedderConfigType;
  onConfigUpdate: (config: EmbedderConfigType) => void;
}

const EmbedderConfig: React.FC<EmbedderConfigProps> = ({ initialConfig, onConfigUpdate }) => {
  const [config, setConfig] = useState<EmbedderConfigType>(
    initialConfig || {
      type: 'huggingface',
      huggingface: {
        model_name: 'sentence-transformers/all-MiniLM-L6-v2',
        device: 'cpu',
        trust_remote_code: false,
        batch_size: 32,
        normalize_embeddings: false,
        show_progress_bar: false,
        convert_to_numpy: true,
        convert_to_tensor: false,
      },
    }
  );
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleTypeChange = (type: EmbedderType) => {
    const newConfig: EmbedderConfigType = { type };
    
    if (type === 'openai') {
      newConfig.openai = {
        api_key: '',
        model_name: 'text-embedding-ada-002',
        timeout: 30,
        batch_size: 100,
        max_retries: 3,
        request_timeout: 30,
        strip_new_lines: true,
        skip_empty: true,
      };
    } else if (type === 'huggingface') {
      newConfig.huggingface = {
        model_name: 'sentence-transformers/all-MiniLM-L6-v2',
        device: 'cpu',
        trust_remote_code: false,
        batch_size: 32,
        normalize_embeddings: false,
        show_progress_bar: false,
        convert_to_numpy: true,
        convert_to_tensor: false,
      };
    }
    
    setConfig(newConfig);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage(null);

    try {
      const response = await configAPI.updateEmbedderConfig(config);
      setMessage({ type: 'success', text: response.message });
      onConfigUpdate(config);
    } catch (error: any) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Failed to update embedder configuration' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Embedder Configuration</h3>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Embedder Type Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Embedder Type
          </label>
          <select
            value={config.type}
            onChange={(e) => handleTypeChange(e.target.value as EmbedderType)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="huggingface">HuggingFace</option>
            <option value="openai">OpenAI</option>
          </select>
        </div>

        {/* OpenAI Configuration */}
        {config.type === 'openai' && (
          <div className="space-y-3 p-4 bg-gray-50 rounded-md">
            <h4 className="font-medium text-gray-800">OpenAI Settings</h4>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                API Key *
              </label>
              <input
                type="password"
                value={config.openai?.api_key || ''}
                onChange={(e) => setConfig({
                  ...config,
                  openai: { ...config.openai!, api_key: e.target.value }
                })}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="sk-..."
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Model Name
              </label>
              <select
                value={config.openai?.model_name || 'text-embedding-ada-002'}
                onChange={(e) => setConfig({
                  ...config,
                  openai: { ...config.openai!, model_name: e.target.value }
                })}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="text-embedding-ada-002">text-embedding-ada-002</option>
                <option value="text-embedding-3-small">text-embedding-3-small</option>
                <option value="text-embedding-3-large">text-embedding-3-large</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Organization (Optional)
              </label>
              <input
                type="text"
                value={config.openai?.organization || ''}
                onChange={(e) => setConfig({
                  ...config,
                  openai: { ...config.openai!, organization: e.target.value }
                })}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="org-..."
              />
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Batch Size
                </label>
                <input
                  type="number"
                  min="1"
                  max="2048"
                  value={config.openai?.batch_size || 100}
                  onChange={(e) => setConfig({
                    ...config,
                    openai: { ...config.openai!, batch_size: parseInt(e.target.value) || 100 }
                  })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Timeout (seconds)
                </label>
                <input
                  type="number"
                  min="1"
                  max="300"
                  value={config.openai?.timeout || 30}
                  onChange={(e) => setConfig({
                    ...config,
                    openai: { ...config.openai!, timeout: parseInt(e.target.value) || 30 }
                  })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Custom Dimensions (Optional)
                </label>
                <input
                  type="number"
                  min="1"
                  value={config.openai?.dimensions || ''}
                  onChange={(e) => setConfig({
                    ...config,
                    openai: { ...config.openai!, dimensions: e.target.value ? parseInt(e.target.value) : undefined }
                  })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Auto-detect"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Retries
                </label>
                <input
                  type="number"
                  min="0"
                  max="10"
                  value={config.openai?.max_retries || 3}
                  onChange={(e) => setConfig({
                    ...config,
                    openai: { ...config.openai!, max_retries: parseInt(e.target.value) || 3 }
                  })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={config.openai?.strip_new_lines || true}
                  onChange={(e) => setConfig({
                    ...config,
                    openai: { ...config.openai!, strip_new_lines: e.target.checked }
                  })}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Strip New Lines</span>
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={config.openai?.skip_empty || true}
                  onChange={(e) => setConfig({
                    ...config,
                    openai: { ...config.openai!, skip_empty: e.target.checked }
                  })}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Skip Empty Texts</span>
              </label>
            </div>
          </div>
        )}

        {/* HuggingFace Configuration */}
        {config.type === 'huggingface' && (
          <div className="space-y-3 p-4 bg-gray-50 rounded-md">
            <h4 className="font-medium text-gray-800">HuggingFace Settings</h4>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Model Name
              </label>
              <input
                type="text"
                value={config.huggingface?.model_name || ''}
                onChange={(e) => setConfig({
                  ...config,
                  huggingface: { ...config.huggingface!, model_name: e.target.value }
                })}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="sentence-transformers/all-MiniLM-L6-v2"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Device
              </label>
              <select
                value={config.huggingface?.device || 'cpu'}
                onChange={(e) => setConfig({
                  ...config,
                  huggingface: { ...config.huggingface!, device: e.target.value }
                })}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="cpu">CPU</option>
                <option value="cuda">CUDA</option>
                <option value="mps">MPS (Apple Silicon)</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cache Directory (Optional)
              </label>
              <input
                type="text"
                value={config.huggingface?.cache_dir || ''}
                onChange={(e) => setConfig({
                  ...config,
                  huggingface: { ...config.huggingface!, cache_dir: e.target.value || undefined }
                })}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="/path/to/cache/dir"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Batch Size
                </label>
                <input
                  type="number"
                  min="1"
                  max="512"
                  value={config.huggingface?.batch_size || 32}
                  onChange={(e) => setConfig({
                    ...config,
                    huggingface: { ...config.huggingface!, batch_size: parseInt(e.target.value) || 32 }
                  })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Max Sequence Length
                </label>
                <input
                  type="number"
                  min="1"
                  value={config.huggingface?.max_seq_length || ''}
                  onChange={(e) => setConfig({
                    ...config,
                    huggingface: { ...config.huggingface!, max_seq_length: e.target.value ? parseInt(e.target.value) : undefined }
                  })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Auto-detect"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Vector Dimensions (Optional)
              </label>
              <input
                type="number"
                min="1"
                value={config.huggingface?.dimensions || ''}
                onChange={(e) => setConfig({
                  ...config,
                  huggingface: { ...config.huggingface!, dimensions: e.target.value ? parseInt(e.target.value) : undefined }
                })}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Auto-detect from model"
              />
            </div>
            
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={config.huggingface?.trust_remote_code || false}
                  onChange={(e) => setConfig({
                    ...config,
                    huggingface: { ...config.huggingface!, trust_remote_code: e.target.checked }
                  })}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Trust Remote Code</span>
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={config.huggingface?.normalize_embeddings || false}
                  onChange={(e) => setConfig({
                    ...config,
                    huggingface: { ...config.huggingface!, normalize_embeddings: e.target.checked }
                  })}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Normalize Embeddings</span>
              </label>
            </div>
          </div>
        )}

        {/* Message */}
        {message && (
          <div className={`p-3 rounded-md ${
            message.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}>
            {message.text}
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Updating...' : 'Update Embedder Configuration'}
        </button>
      </form>
    </div>
  );
};

export default EmbedderConfig; 