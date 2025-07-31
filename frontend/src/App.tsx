import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Settings, Upload, Search, FileText, Activity } from 'lucide-react';

// Components
import EmbedderConfig from './components/config/EmbedderConfig';
import VectorDBConfig from './components/config/VectorDBConfig';
import DocumentUploader from './components/upload/DocumentUploader';
import DocumentList from './components/results/DocumentList';
import SearchInterface from './components/results/SearchInterface';

// Services
import { configAPI, generalAPI } from './services/api';
import { AppConfig, HealthStatus, DocumentUploadResponse } from './types/api';

// Layout Components
const Sidebar: React.FC = () => {
  const location = useLocation();
  
  const isActive = (path: string) => location.pathname === path;
  
  const linkClass = (path: string) => `
    flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors
    ${isActive(path) 
      ? 'bg-blue-100 text-blue-700' 
      : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'}
  `;

  return (
    <div className="w-64 bg-white shadow-md h-screen overflow-y-auto">
      <div className="p-6">
        <h1 className="text-xl font-bold text-gray-900">Document Embedder</h1>
        <p className="text-sm text-gray-600 mt-1">AI-Powered Document Platform</p>
      </div>
      
      <nav className="px-4 space-y-1">
        <Link to="/" className={linkClass('/')}>
          <Upload className="w-4 h-4" />
          <span>Upload & Process</span>
        </Link>
        
        <Link to="/search" className={linkClass('/search')}>
          <Search className="w-4 h-4" />
          <span>Search Documents</span>
        </Link>
        
        <Link to="/documents" className={linkClass('/documents')}>
          <FileText className="w-4 h-4" />
          <span>Document Library</span>
        </Link>
        
        <Link to="/config" className={linkClass('/config')}>
          <Settings className="w-4 h-4" />
          <span>Configuration</span>
        </Link>
        
        <Link to="/health" className={linkClass('/health')}>
          <Activity className="w-4 h-4" />
          <span>System Health</span>
        </Link>
      </nav>
    </div>
  );
};

// Page Components
const UploadPage: React.FC<{ onUpload: () => void }> = ({ onUpload }) => {
  const handleUploadComplete = (response: DocumentUploadResponse) => {
    console.log('Upload completed:', response);
    onUpload();
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Upload & Process Documents</h2>
        <p className="text-gray-600 mt-1">Upload documents to be processed and embedded for search</p>
      </div>
      
      <DocumentUploader onUploadComplete={handleUploadComplete} />
    </div>
  );
};

const SearchPage: React.FC = () => (
  <div className="space-y-6">
    <div>
      <h2 className="text-2xl font-bold text-gray-900">Search Documents</h2>
      <p className="text-gray-600 mt-1">Find relevant information across your document collection</p>
    </div>
    
    <SearchInterface />
  </div>
);

const DocumentsPage: React.FC<{ refreshTrigger: number }> = ({ refreshTrigger }) => (
  <div className="space-y-6">
    <div>
      <h2 className="text-2xl font-bold text-gray-900">Document Library</h2>
      <p className="text-gray-600 mt-1">Manage your uploaded documents and view processing status</p>
    </div>
    
    <DocumentList refreshTrigger={refreshTrigger} />
  </div>
);

const ConfigPage: React.FC<{ onConfigUpdate: () => void }> = ({ onConfigUpdate }) => {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await configAPI.getCurrentConfig();
        setConfig(response.config || null);
      } catch (error) {
        console.error('Failed to fetch config:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchConfig();
  }, []);

  const handleConfigUpdate = () => {
    onConfigUpdate();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <span className="ml-2 text-gray-600">Loading configuration...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">System Configuration</h2>
        <p className="text-gray-600 mt-1">Configure your embedder and vector database settings</p>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <EmbedderConfig 
          initialConfig={config?.embedder} 
          onConfigUpdate={handleConfigUpdate}
        />
        <VectorDBConfig 
          initialConfig={config?.vector_db} 
          onConfigUpdate={handleConfigUpdate}
        />
      </div>
    </div>
  );
};

const HealthPage: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = async () => {
    try {
      setLoading(true);
      const response = await configAPI.checkServiceHealth();
      setHealth(response);
    } catch (error) {
      console.error('Failed to fetch health:', error);
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        <span className="ml-2 text-gray-600">Checking system health...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">System Health</h2>
          <p className="text-gray-600 mt-1">Monitor the status of your embedder and vector database</p>
        </div>
        <button
          onClick={fetchHealth}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>
      
      {health ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Embedder Health */}
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h3 className="text-lg font-semibold mb-4">Embedder Status</h3>
            <div className={`flex items-center space-x-2 mb-3 ${
              health.embedder.healthy ? 'text-green-600' : 'text-red-600'
            }`}>
              <div className={`w-3 h-3 rounded-full ${
                health.embedder.healthy ? 'bg-green-500' : 'bg-red-500'
              }`}></div>
              <span className="font-medium">
                {health.embedder.healthy ? 'Healthy' : 'Unhealthy'}
              </span>
            </div>
            {health.embedder.info && (
              <div className="text-sm text-gray-600 space-y-1">
                <p><strong>Provider:</strong> {health.embedder.info.provider}</p>
                <p><strong>Model:</strong> {health.embedder.info.model_name}</p>
                <p><strong>Dimension:</strong> {health.embedder.info.dimension}</p>
              </div>
            )}
            {health.embedder.error && (
              <p className="text-sm text-red-600 mt-2">{health.embedder.error}</p>
            )}
          </div>

          {/* Vector DB Health */}
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h3 className="text-lg font-semibold mb-4">Vector Database Status</h3>
            <div className={`flex items-center space-x-2 mb-3 ${
              health.vector_db.healthy ? 'text-green-600' : 'text-red-600'
            }`}>
              <div className={`w-3 h-3 rounded-full ${
                health.vector_db.healthy ? 'bg-green-500' : 'bg-red-500'
              }`}></div>
              <span className="font-medium">
                {health.vector_db.healthy ? 'Healthy' : 'Unhealthy'}
              </span>
            </div>
            {health.vector_db.stats && (
              <div className="text-sm text-gray-600 space-y-1">
                <p><strong>Total Vectors:</strong> {health.vector_db.stats.total_vectors || 0}</p>
                {health.vector_db.stats.collection_name && (
                  <p><strong>Collection:</strong> {health.vector_db.stats.collection_name}</p>
                )}
              </div>
            )}
            {health.vector_db.error && (
              <p className="text-sm text-red-600 mt-2">{health.vector_db.error}</p>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white p-6 rounded-lg shadow-md text-center">
          <p className="text-gray-600">Failed to fetch system health status</p>
        </div>
      )}
    </div>
  );
};

// Main App Component
const App: React.FC = () => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUpload = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  const handleConfigUpdate = () => {
    // Could trigger health check refresh or other updates
  };

  return (
    <Router>
      <div className="flex h-screen bg-gray-100">
        <Sidebar />
        
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-6 py-8">
            <Routes>
              <Route path="/" element={<UploadPage onUpload={handleUpload} />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/documents" element={<DocumentsPage refreshTrigger={refreshTrigger} />} />
              <Route path="/config" element={<ConfigPage onConfigUpdate={handleConfigUpdate} />} />
              <Route path="/health" element={<HealthPage />} />
            </Routes>
          </div>
        </main>
      </div>
    </Router>
  );
};

export default App; 