# 🚀 Quick Start Guide

## Starting the Application

### Option 1: Use the Start Script (Recommended)

1. **Start Backend Server:**
   ```bash
   python start_backend.py
   ```
   This will:
   - Create a virtual environment if needed
   - Install dependencies
   - Start the FastAPI server on http://localhost:8000

2. **Start Frontend (in a new terminal):**
   ```bash
   cd frontend
   npm install    # First time only
   npm start
   ```
   This will start the React app on http://localhost:3000

### Option 2: Manual Setup

**Backend:**
```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm start
```

## Configuration

1. **Configure Services** (via the web interface):
   - Go to http://localhost:3000/config
   - Set up your Embedder (OpenAI or HuggingFace)
   - Set up your Vector Database (Pinecone, ChromaDB, or Qdrant)
   - Set up your Chat Model (OpenAI, Gemini, or Local)

2. **Environment Variables** (optional):
   - Copy `backend/.env.example` to `backend/.env`
   - Add your API keys for external services

## Troubleshooting

### CORS Errors
- **Problem**: "Access to XMLHttpRequest has been blocked by CORS policy"
- **Solution**: Make sure the backend server is running on http://localhost:8000

### Backend Not Starting
- **Problem**: Module import errors or dependency issues
- **Solution**: 
  1. Make sure you're in the virtual environment
  2. Run `pip install -r requirements.txt` again
  3. Check Python version (3.8+ required)

### Frontend Build Errors
- **Problem**: TypeScript or React errors
- **Solution**:
  1. Delete `node_modules` and `package-lock.json`
  2. Run `npm install` again
  3. Make sure Node.js 16+ is installed

### Chat Not Working
- **Problem**: "Backend server not available" or service not ready
- **Solution**:
  1. Ensure backend is running on port 8000
  2. Configure at least one embedder and vector database
  3. Configure a chat model in the settings

## Service URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Chat Health Check**: http://localhost:8000/chat/health
- **System Health**: http://localhost:8000/config/health