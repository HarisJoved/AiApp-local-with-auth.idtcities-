import React, { useState } from 'react';
import { VectorDBConfig as VectorDBConfigType, VectorDBType } from '../../types/api';
import { configAPI } from '../../services/api';

interface VectorDBConfigProps {
  initialConfig?: VectorDBConfigType;
  onConfigUpdate: (config: VectorDBConfigType) => void;
}

const VectorDBConfig: React.FC<VectorDBConfigProps> = ({ initialConfig, onConfigUpdate }) => {
  const [config, setConfig] = useState<VectorDBConfigType>(
    initialConfig || {
      type: 'chromadb',
      chromadb: {
        host: 'localhost',
        port: 8000,
        collection_name: 'documents',
      },
    }
  );
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleTypeChange = (type: VectorDBType) => {
    const newConfig: VectorDBConfigType = { type };
    
    if (type === 'pinecone') {
      newConfig.pinecone = {
        api_key: '',
        environment: 'us-east1-gcp',
        index_name: 'documents',
        dimension: 1536,
        metric: 'cosine',
      };
    } else if (type === 'chromadb') {
      newConfig.chromadb = {
        host: 'localhost',
        port: 8000,
        collection_name: 'documents',
      };
    } else if (type === 'qdrant') {
      newConfig.qdrant = {
        host: 'localhost',
        port: 6333,
        collection_name: 'documents',
        https: false,
      };
    }
    
    setConfig(newConfig);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage(null);

    try {
      const response = await configAPI.updateVectorDBConfig(config);
      setMessage({ type: 'success', text: response.message });
      onConfigUpdate(config);
    } catch (error: any) {
      setMessage({ 
        type: 'error', 
        text: error.response?.data?.detail || 'Failed to update vector database configuration' 
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Vector Database Configuration</h3>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Vector DB Type Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Vector Database Type
          </label>
          <select
            value={config.type}
            onChange={(e) => handleTypeChange(e.target.value as VectorDBType)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="chromadb">ChromaDB</option>
            <option value="pinecone">Pinecone</option>
            <option value="qdrant">Qdrant</option>
          </select>
        </div>

        {/* Pinecone Configuration */}
        {config.type === 'pinecone' && (
          <div className="space-y-3 p-4 bg-gray-50 rounded-md">
            <h4 className="font-medium text-gray-800">Pinecone Settings</h4>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                API Key *
              </label>
              <input
                type="password"
                value={config.pinecone?.api_key || ''}
                onChange={(e) => setConfig({
                  ...config,
                  pinecone: { ...config.pinecone!, api_key: e.target.value }
                })}
                required
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Your Pinecone API key"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Environment
              </label>
              <input
                type="text"
                value={config.pinecone?.environment || ''}
                onChange={(e) => setConfig({
                  ...config,
                  pinecone: { ...config.pinecone!, environment: e.target.value }
                })}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="us-east1-gcp"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Index Name
              </label>
              <input
                type="text"
                value={config.pinecone?.index_name || ''}
                onChange={(e) => setConfig({
                  ...config,
                  pinecone: { ...config.pinecone!, index_name: e.target.value }
                })}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="documents"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Dimension
                </label>
                <input
                  type="number"
                  value={config.pinecone?.dimension || 1536}
                  onChange={(e) => setConfig({
                    ...config,
                    pinecone: { ...config.pinecone!, dimension: parseInt(e.target.value) }
                  })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Metric
                </label>
                <select
                  value={config.pinecone?.metric || 'cosine'}
                  onChange={(e) => setConfig({
                    ...config,
                    pinecone: { ...config.pinecone!, metric: e.target.value }
                  })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="cosine">Cosine</option>
                  <option value="euclidean">Euclidean</option>
                  <option value="dotproduct">Dot Product</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* ChromaDB Configuration */}
        {config.type === 'chromadb' && (
          <div className="space-y-3 p-4 bg-gray-50 rounded-md">
            <h4 className="font-medium text-gray-800">ChromaDB Settings</h4>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Host
                </label>
                <input
                  type="text"
                  value={config.chromadb?.host || ''}
                  onChange={(e) => setConfig({
                    ...config,
                    chromadb: { ...config.chromadb!, host: e.target.value }
                  })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="localhost"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Port
                </label>
                <input
                  type="number"
                  value={config.chromadb?.port || 8000}
                  onChange={(e) => setConfig({
                    ...config,
                    chromadb: { ...config.chromadb!, port: parseInt(e.target.value) }
                  })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Collection Name
              </label>
              <input
                type="text"
                value={config.chromadb?.collection_name || ''}
                onChange={(e) => setConfig({
                  ...config,
                  chromadb: { ...config.chromadb!, collection_name: e.target.value }
                })}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="documents"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Persist Directory (Optional)
              </label>
              <input
                type="text"
                value={config.chromadb?.persist_directory || ''}
                onChange={(e) => setConfig({
                  ...config,
                  chromadb: { ...config.chromadb!, persist_directory: e.target.value }
                })}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="/path/to/chroma/data"
              />
              <p className="text-xs text-gray-500 mt-1">
                Leave empty for in-memory storage
              </p>
            </div>
          </div>
        )}

        {/* Qdrant Configuration */}
        {config.type === 'qdrant' && (
          <div className="space-y-3 p-4 bg-gray-50 rounded-md">
            <h4 className="font-medium text-gray-800">Qdrant Settings</h4>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Host
                </label>
                <input
                  type="text"
                  value={config.qdrant?.host || ''}
                  onChange={(e) => setConfig({
                    ...config,
                    qdrant: { ...config.qdrant!, host: e.target.value }
                  })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="localhost"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Port
                </label>
                <input
                  type="number"
                  value={config.qdrant?.port || 6333}
                  onChange={(e) => setConfig({
                    ...config,
                    qdrant: { ...config.qdrant!, port: parseInt(e.target.value) }
                  })}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Collection Name
              </label>
              <input
                type="text"
                value={config.qdrant?.collection_name || ''}
                onChange={(e) => setConfig({
                  ...config,
                  qdrant: { ...config.qdrant!, collection_name: e.target.value }
                })}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="documents"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                API Key (Optional)
              </label>
              <input
                type="password"
                value={config.qdrant?.api_key || ''}
                onChange={(e) => setConfig({
                  ...config,
                  qdrant: { ...config.qdrant!, api_key: e.target.value }
                })}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Optional API key"
              />
            </div>
            
            <div>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={config.qdrant?.https || false}
                  onChange={(e) => setConfig({
                    ...config,
                    qdrant: { ...config.qdrant!, https: e.target.checked }
                  })}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Use HTTPS</span>
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
          {isLoading ? 'Updating...' : 'Update Vector Database Configuration'}
        </button>
      </form>
    </div>
  );
};

export default VectorDBConfig; 