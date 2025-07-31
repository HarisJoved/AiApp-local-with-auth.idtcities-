# Document Embedding Platform

A modular, full-stack document processing and embedding platform built with FastAPI and React. Upload documents, process them with selectable embedding models, store vectors in configurable vector databases, and perform semantic search across your document collection.

![Platform Architecture](docs/images/architecture.png)

## ✨ Features

### 🔧 Modular Architecture
- **Pluggable Embedders**: Support for OpenAI and HuggingFace embedding models
- **Multiple Vector Databases**: Pinecone, ChromaDB, and Qdrant support
- **Document Processors**: LangChain-based processors for PDF, DOCX, TXT, HTML, and Markdown

### 🚀 Full-Stack Application
- **FastAPI Backend**: High-performance async API with automatic documentation
- **React Frontend**: Modern, responsive UI with TypeScript and Tailwind CSS
- **Real-time Updates**: Live document processing status and search results

### 📄 Document Processing
- **Multi-format Support**: PDF, DOCX, TXT, HTML, Markdown
- **Intelligent Chunking**: Configurable text splitting with overlap
- **Batch Processing**: Async document processing with status tracking

### 🔍 Semantic Search
- **Vector Similarity Search**: Find relevant content across documents
- **Advanced Filtering**: Search with metadata filters and similarity thresholds
- **Fast Results**: Optimized search with execution time tracking

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend │    │  FastAPI Backend │    │ Vector Database │
│                 │────│                 │────│                 │
│ • Configuration │    │ • Document API  │    │ • Pinecone      │
│ • Upload UI     │    │ • Search API    │    │ • ChromaDB      │
│ • Search UI     │    │ • Config API    │    │ • Qdrant        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                       ┌─────────────────┐
                       │   Core Modules  │
                       │                 │
                       │ • DocumentProc  │
                       │ • Embedders     │
                       │ • VectorDBs     │
                       └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **Git**

### 1. Clone the Repository

```bash
git clone <repository-url>
cd document-embedding-platform
```

### 2. Automated Setup

Run the setup script to configure both backend and frontend:

```bash
python scripts/setup.py
```

This will:
- Create Python virtual environment
- Install Python dependencies
- Install Node.js dependencies
- Create environment configuration files
- Set up necessary directories

### 3. Configure Your Services

Edit `backend/.env` to configure your embedding and vector database services:

```bash
# For OpenAI Embeddings
OPENAI_API_KEY=your_openai_api_key

# For Pinecone Vector Database
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=us-east1-gcp
```

### 4. Start the Application

#### Option A: Use the Start Script (Recommended)
```bash
bash scripts/start.sh
```

#### Option B: Start Manually
```bash
# Terminal 1 - Start Backend
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python -m uvicorn app.main:app --reload

# Terminal 2 - Start Frontend
cd frontend
npm start
```

### 5. Access the Application

- **Frontend Application**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health

## 📖 Usage Guide

### 1. Configure Your System

1. **Navigate to Configuration**: Click the "Configuration" tab in the sidebar
2. **Set up Embedder**: Choose between OpenAI or HuggingFace and provide credentials
3. **Set up Vector Database**: Choose between Pinecone, ChromaDB, or Qdrant and configure connection

### 2. Upload Documents

1. **Go to Upload & Process**: Main dashboard for document upload
2. **Drag & Drop**: Upload supported file formats (PDF, DOCX, TXT, HTML, Markdown)
3. **Monitor Progress**: Watch real-time processing status

### 3. Search Documents

1. **Navigate to Search**: Use the search interface
2. **Enter Query**: Type your search question
3. **Adjust Parameters**: Set number of results and similarity threshold
4. **Review Results**: Browse ranked results with similarity scores

### 4. Manage Documents

1. **Document Library**: View all uploaded documents
2. **Check Status**: Monitor processing progress
3. **Delete Documents**: Remove documents and their vectors

## 🔧 Configuration Options

### Embedding Models

#### OpenAI
```python
{
  "type": "openai",
  "openai": {
    "api_key": "sk-...",
    "model_name": "text-embedding-ada-002",
    "organization": "org-...",  # Optional
    "timeout": 30
  }
}
```

#### HuggingFace
```python
{
  "type": "huggingface",
  "huggingface": {
    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
    "device": "cpu",  # or "cuda", "mps"
    "trust_remote_code": false,
    "cache_dir": "/path/to/cache"  # Optional
  }
}
```

### Vector Databases

#### Pinecone
```python
{
  "type": "pinecone",
  "pinecone": {
    "api_key": "your-api-key",
    "environment": "us-east1-gcp",
    "index_name": "documents",
    "dimension": 1536,
    "metric": "cosine"
  }
}
```

#### ChromaDB
```python
{
  "type": "chromadb",
  "chromadb": {
    "host": "localhost",
    "port": 8000,
    "collection_name": "documents",
    "persist_directory": "/path/to/data"  # Optional for local storage
  }
}
```

#### Qdrant
```python
{
  "type": "qdrant",
  "qdrant": {
    "host": "localhost",
    "port": 6333,
    "collection_name": "documents",
    "api_key": "your-api-key",  # Optional
    "https": false
  }
}
```

## 🔌 API Reference

### Core Endpoints

#### Document Upload
```bash
POST /upload/
Content-Type: multipart/form-data

# Upload a document file
curl -X POST "http://localhost:8000/upload/" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

#### Search Documents
```bash
POST /upload/search
Content-Type: application/json

{
  "query": "machine learning algorithms",
  "top_k": 5,
  "threshold": 0.7
}
```

#### Configuration
```bash
# Get current configuration
GET /config/

# Update embedder configuration
POST /config/embedder
{
  "type": "openai",
  "openai": {
    "api_key": "sk-...",
    "model_name": "text-embedding-ada-002"
  }
}

# Update vector database configuration
POST /config/vector-db
{
  "type": "pinecone",
  "pinecone": {
    "api_key": "your-key",
    "environment": "us-east1-gcp",
    "index_name": "documents"
  }
}
```

## 🧪 Development

### Backend Development

```bash
cd backend

# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest

# Code formatting
black .
isort .

# Type checking
mypy .
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

## 📁 Project Structure

```
document-embedding-platform/
├── backend/
│   ├── app/
│   │   ├── core/                 # Core business logic
│   │   │   ├── document_processor/
│   │   │   ├── embedders/
│   │   │   └── vector_db/
│   │   ├── models/               # Pydantic models
│   │   ├── routers/              # FastAPI routes
│   │   ├── services/             # Business services
│   │   ├── config/               # Configuration management
│   │   └── main.py               # FastAPI application
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/           # React components
│   │   │   ├── config/
│   │   │   ├── upload/
│   │   │   └── results/
│   │   ├── services/             # API services
│   │   ├── types/                # TypeScript types
│   │   ├── App.tsx               # Main app component
│   │   └── index.tsx             # App entry point
│   ├── package.json
│   └── .env.example
├── scripts/
│   ├── setup.py                 # Setup automation
│   └── start.sh                 # Start script
├── docs/                        # Documentation
└── README.md
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `/docs` endpoint when running the backend
- **Issues**: Report bugs and request features via GitHub Issues
- **Health Check**: Monitor system status at `/health` endpoint

## 🙏 acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://reactjs.org/) - Frontend library
- [LangChain](https://langchain.com/) - Document processing framework
- [OpenAI](https://openai.com/) - Embedding models
- [HuggingFace](https://huggingface.co/) - Open-source ML models
- [Pinecone](https://pinecone.io/) - Vector database
- [ChromaDB](https://chroma.com/) - Open-source vector database
- [Qdrant](https://qdrant.tech/) - Vector search engine 