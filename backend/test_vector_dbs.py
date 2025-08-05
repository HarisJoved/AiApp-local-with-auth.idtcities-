#!/usr/bin/env python3
"""
Test script to verify both Pinecone and ChromaDB clients work correctly.
Run this after configuring your services to test the vector database functionality.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.models.config import PineconeDBConfig, ChromaDBConfig
from app.models.document import DocumentChunk
from app.core.vector_db.pinecone_client import PineconeClient
from app.core.vector_db.chromadb_client import ChromaDBClient


async def test_pinecone():
    """Test Pinecone client functionality"""
    print("🔵 Testing Pinecone client...")
    
    # Sample config (you'll need to provide real values)
    config = PineconeDBConfig(
        api_key="your-pinecone-api-key",  # Replace with actual key
        environment="us-east1-aws",       # Replace with your environment
        index_name="test-documents",      # Will be created if doesn't exist
        dimension=384,                    # Adjust based on your embedder
        metric="cosine"
    )
    
    try:
        client = PineconeClient(config)
        
        # Test initialization
        print("  Initializing...")
        await client.initialize()
        print("  ✅ Initialization successful")
        
        # Test health check
        print("  Checking health...")
        is_healthy = await client.health_check()
        print(f"  ✅ Health check: {'healthy' if is_healthy else 'unhealthy'}")
        
        # Test search method (the one causing issues)
        print("  Testing search method...")
        dummy_embedding = [0.1] * 384  # Create dummy embedding
        results = await client.search(
            query_embedding=dummy_embedding,
            top_k=5,
            similarity_threshold=0.0
        )
        print(f"  ✅ Search successful, found {len(results)} results")
        
        # Test collection stats
        print("  Getting collection stats...")
        stats = await client.get_collection_stats()
        print(f"  ✅ Stats: {stats.get('total_vectors', 0)} vectors")
        
        print("  🎉 Pinecone test completed successfully!")
        return True
        
    except Exception as e:
        print(f"  ❌ Pinecone test failed: {e}")
        return False


async def test_chromadb():
    """Test ChromaDB client functionality"""
    print("🟢 Testing ChromaDB client...")
    
    # Sample config
    config = ChromaDBConfig(
        host="localhost",
        port=8000,
        collection_name="test-documents",
        persist_directory="./chroma_db"  # Local persistent storage
    )
    
    try:
        client = ChromaDBClient(config)
        
        # Test initialization
        print("  Initializing...")
        await client.initialize()
        print("  ✅ Initialization successful")
        
        # Test health check
        print("  Checking health...")
        is_healthy = await client.health_check()
        print(f"  ✅ Health check: {'healthy' if is_healthy else 'unhealthy'}")
        
        # Test search method (the one causing issues)
        print("  Testing search method...")
        dummy_embedding = [0.1] * 384  # Create dummy embedding
        results = await client.search(
            query_embedding=dummy_embedding,
            top_k=5,
            similarity_threshold=0.0
        )
        print(f"  ✅ Search successful, found {len(results)} results")
        
        # Test collection stats
        print("  Getting collection stats...")
        stats = await client.get_collection_stats()
        print(f"  ✅ Stats: {stats.get('total_vectors', 0)} vectors")
        
        print("  🎉 ChromaDB test completed successfully!")
        return True
        
    except Exception as e:
        print(f"  ❌ ChromaDB test failed: {e}")
        return False


async def main():
    """Main test function"""
    print("🧪 Vector Database Client Test")
    print("================================")
    
    # Test both clients
    pinecone_success = await test_pinecone()
    print()
    chromadb_success = await test_chromadb()
    
    print("\n📊 Test Results:")
    print("================")
    print(f"Pinecone: {'✅ PASS' if pinecone_success else '❌ FAIL'}")
    print(f"ChromaDB: {'✅ PASS' if chromadb_success else '❌ FAIL'}")
    
    if pinecone_success and chromadb_success:
        print("\n🎉 All tests passed! Your vector databases are working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the configuration and try again.")
        print("\nCommon issues:")
        print("- Pinecone: Check API key and environment settings")
        print("- ChromaDB: Make sure ChromaDB server is running (if using remote)")
        print("- Network: Check firewall and connection settings")


if __name__ == "__main__":
    asyncio.run(main())