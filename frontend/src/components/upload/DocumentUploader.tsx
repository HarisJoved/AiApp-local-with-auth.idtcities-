import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import { uploadAPI } from '../../services/api';
import { DocumentUploadResponse } from '../../types/api';

interface DocumentUploaderProps {
  onUploadComplete: (response: DocumentUploadResponse) => void;
}

const DocumentUploader: React.FC<DocumentUploaderProps> = ({ onUploadComplete }) => {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    setUploading(true);
    setMessage(null);

    try {
      const response = await uploadAPI.uploadDocument(file);
      setMessage({ type: 'success', text: response.message });
      onUploadComplete(response);
    } catch (error: any) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to upload document'
      });
    } finally {
      setUploading(false);
    }
  }, [onUploadComplete]);

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'text/html': ['.html'],
      'text/markdown': ['.md', '.markdown'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls']
    },
    multiple: false,
    maxSize: 10 * 1024 * 1024, // 10MB
  });

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Upload Document</h3>
      
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <input {...getInputProps()} />
        
        <div className="flex flex-col items-center space-y-3">
          {uploading ? (
            <Loader className="w-12 h-12 text-blue-500 animate-spin" />
          ) : (
            <Upload className="w-12 h-12 text-gray-400" />
          )}
          
          <div>
            <p className="text-lg font-medium text-gray-700">
              {uploading ? 'Uploading...' : isDragActive ? 'Drop file here' : 'Drag & drop a document'}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              {uploading ? 'Please wait while we process your file' : 'or click to select a file'}
            </p>
          </div>
          
          <div className="text-xs text-gray-400">
            Supported formats: PDF, DOCX, TXT, HTML, Markdown, PPTX, XLSX, XLS
            <br />
            Maximum file size: 10MB
          </div>
        </div>
      </div>

      {/* Selected File Info */}
      {acceptedFiles.length > 0 && !uploading && (
        <div className="mt-4 p-3 bg-gray-50 rounded-md">
          <div className="flex items-center space-x-2">
            <File className="w-4 h-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700">
              {acceptedFiles[0].name}
            </span>
            <span className="text-xs text-gray-500">
              ({(acceptedFiles[0].size / 1024 / 1024).toFixed(2)} MB)
            </span>
          </div>
        </div>
      )}

      {/* Upload Message */}
      {message && (
        <div className={`mt-4 p-3 rounded-md flex items-center space-x-2 ${
          message.type === 'success' 
            ? 'bg-green-100 text-green-800' 
            : 'bg-red-100 text-red-800'
        }`}>
          {message.type === 'success' ? (
            <CheckCircle className="w-4 h-4" />
          ) : (
            <AlertCircle className="w-4 h-4" />
          )}
          <span className="text-sm">{message.text}</span>
        </div>
      )}
    </div>
  );
};

export default DocumentUploader; 