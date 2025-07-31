import React, { useState } from 'react';
import { Search, FileText, Clock } from 'lucide-react';
import { uploadAPI } from '../../services/api';
import { SearchRequest, SearchResponse, SearchResult } from '../../types/api';

const SearchInterface: React.FC = () => {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [threshold, setThreshold] = useState(0.0);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!query.trim()) {
      setError('Please enter a search query');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const request: SearchRequest = {
        query: query.trim(),
        top_k: topK,
        threshold: threshold
      };

      const response = await uploadAPI.searchDocuments(request);
      setResults(response.results);
      setSearchResponse(response);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to search documents');
      setResults([]);
      setSearchResponse(null);
    } finally {
      setLoading(false);
    }
  };

  const formatScore = (score: number) => (score * 100).toFixed(1);

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Search Documents</h3>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="space-y-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Search Query
          </label>
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter your search query..."
              className="w-full border border-gray-300 rounded-md pl-10 pr-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Number of Results
            </label>
            <select
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value))}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={3}>3</option>
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Minimum Score ({(threshold * 100).toFixed(0)}%)
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
              className="w-full"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
        >
          {loading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
              <span>Searching...</span>
            </>
          ) : (
            <>
              <Search className="w-4 h-4" />
              <span>Search</span>
            </>
          )}
        </button>
      </form>

      {/* Error Message */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-md mb-4">
          {error}
        </div>
      )}

      {/* Search Results */}
      {searchResponse && (
        <div className="space-y-4">
          <div className="flex items-center justify-between py-2 border-b border-gray-200">
            <h4 className="font-medium text-gray-900">
              Search Results ({searchResponse.total_results})
            </h4>
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <Clock className="w-4 h-4" />
              <span>{(searchResponse.execution_time * 1000).toFixed(0)}ms</span>
            </div>
          </div>

          {results.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No results found for "{searchResponse.query}"</p>
              <p className="text-sm">Try adjusting your search query or lowering the minimum score</p>
            </div>
          ) : (
            <div className="space-y-4">
              {results.map((result, index) => (
                <div
                  key={result.chunk_id}
                  className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center space-x-2">
                      <FileText className="w-4 h-4 text-blue-500" />
                      <span className="font-medium text-gray-900">
                        {result.document_id}
                      </span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-500">
                        #{index + 1}
                      </span>
                      <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded-full">
                        {formatScore(result.score)}% match
                      </span>
                    </div>
                  </div>

                  <p className="text-gray-700 text-sm leading-relaxed mb-2">
                    {result.content}
                  </p>

                  {result.metadata && Object.keys(result.metadata).length > 0 && (
                    <div className="text-xs text-gray-500 border-t border-gray-100 pt-2">
                      <span>Metadata: </span>
                      {Object.entries(result.metadata)
                        .filter(([key]) => !['content', 'chunk_id'].includes(key))
                        .map(([key, value]) => (
                          <span key={key} className="mr-3">
                            {key}: {String(value)}
                          </span>
                        ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SearchInterface; 