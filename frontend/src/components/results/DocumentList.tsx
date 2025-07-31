import React, { useState, useEffect } from 'react';
import { File, Clock, CheckCircle, AlertCircle, Trash2, Eye } from 'lucide-react';
import { uploadAPI } from '../../services/api';
import { Document, DocumentStatus } from '../../types/api';

interface DocumentListProps {
  refreshTrigger: number;
}

const DocumentList: React.FC<DocumentListProps> = ({ refreshTrigger }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const response = await uploadAPI.listDocuments();
      setDocuments(response.documents);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [refreshTrigger]);

  const handleDelete = async (documentId: string) => {
    if (!window.confirm('Are you sure you want to delete this document?')) {
      return;
    }

    try {
      await uploadAPI.deleteDocument(documentId);
      setDocuments(docs => docs.filter(doc => doc.id !== documentId));
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete document');
    }
  };

  const getStatusIcon = (status: DocumentStatus) => {
    switch (status) {
      case 'uploaded':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'processing':
        return <Clock className="w-4 h-4 text-blue-500 animate-pulse" />;
      case 'processed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'embedded':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStatusText = (status: DocumentStatus) => {
    switch (status) {
      case 'uploaded':
        return 'Uploaded';
      case 'processing':
        return 'Processing';
      case 'processed':
        return 'Processed';
      case 'embedded':
        return 'Ready';
      case 'error':
        return 'Error';
      default:
        return 'Unknown';
    }
  };

  const getStatusColor = (status: DocumentStatus) => {
    switch (status) {
      case 'uploaded':
        return 'text-yellow-700 bg-yellow-100';
      case 'processing':
        return 'text-blue-700 bg-blue-100';
      case 'processed':
        return 'text-green-700 bg-green-100';
      case 'embedded':
        return 'text-green-800 bg-green-200';
      case 'error':
        return 'text-red-700 bg-red-100';
      default:
        return 'text-gray-700 bg-gray-100';
    }
  };

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">Documents</h3>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-2 text-gray-600">Loading documents...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold mb-4">Documents</h3>
        <div className="text-red-600 text-center py-8">
          <AlertCircle className="w-8 h-8 mx-auto mb-2" />
          <p>{error}</p>
          <button
            onClick={fetchDocuments}
            className="mt-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Documents ({documents.length})</h3>
        <button
          onClick={fetchDocuments}
          className="text-blue-600 hover:text-blue-800 text-sm"
        >
          Refresh
        </button>
      </div>

      {documents.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <File className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No documents uploaded yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3 flex-1">
                  <File className="w-5 h-5 text-gray-400 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium text-gray-900 truncate">
                      {doc.filename}
                    </h4>
                    <div className="flex items-center space-x-4 mt-1 text-sm text-gray-500">
                      <span className="capitalize">{doc.file_type}</span>
                      <span>{doc.chunks_count} chunks</span>
                      <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                    </div>
                    {doc.error_message && (
                      <p className="text-red-600 text-sm mt-1">
                        {doc.error_message}
                      </p>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center space-x-2 ml-4">
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(doc.status)}`}>
                    {getStatusIcon(doc.status)}
                    <span className="ml-1">{getStatusText(doc.status)}</span>
                  </span>
                  
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                    title="Delete document"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default DocumentList; 