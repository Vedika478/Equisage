"""
Agentic RAG using ChromaDB for macro economic knowledge.
Demonstrates Competition Concept #4: Agentic RAG
"""

import chromadb
from chromadb.config import Settings
import json
import os
from typing import List, Dict, Any


# ChromaDB persistent storage path
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
KNOWLEDGE_BASE_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base.json")

# Initialize ChromaDB client (persistent)
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)


def initialize_knowledge_base() -> Dict[str, Any]:
    """
    Load knowledge_base.json and embed all chunks into ChromaDB.
    Run this once during setup or when knowledge base is updated.
    
    Returns:
        Dict with initialization status
    """
    try:
        # Load knowledge base
        with open(KNOWLEDGE_BASE_PATH, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        
        # Get or create collection
        collection = chroma_client.get_or_create_collection(
            name="macro_knowledge",
            metadata={"description": "India macro economic knowledge for equity research"}
        )
        
        # Extract chunks
        chunks = kb_data.get("macro_knowledge", [])
        
        if not chunks:
            return {"success": False, "error": "No knowledge chunks found"}
        
        # Prepare data for ChromaDB
        documents = [chunk["text"] for chunk in chunks]
        ids = [chunk["id"] for chunk in chunks]
        metadatas = [{"category": chunk["category"]} for chunk in chunks]
        
        # Add to collection (will handle embeddings automatically)
        collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )
        
        return {
            "success": True,
            "chunks_loaded": len(chunks),
            "collection": "macro_knowledge",
            "path": CHROMA_DB_PATH
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def query_knowledge(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Query ChromaDB for relevant macro knowledge chunks.
    This is called by Macro Agent (Agentic RAG).
    
    Args:
        query: Natural language query (e.g., "India inflation trends")
        top_k: Number of relevant chunks to retrieve
        
    Returns:
        List of dicts with text and relevance score
    """
    try:
        # Get collection
        collection = chroma_client.get_collection(name="macro_knowledge")
        
        # Query
        results = collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        # Format results
        chunks = []
        if results and results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                chunks.append({
                    "text": doc,
                    "category": results['metadatas'][0][i].get("category", "unknown"),
                    "relevance": 1.0 - results['distances'][0][i] if results['distances'] else 0.0
                })
        
        return chunks
        
    except Exception as e:
        # Return empty if collection doesn't exist yet
        return []


def get_collection_stats() -> Dict[str, Any]:
    """
    Get statistics about the knowledge base collection.
    Used for health checks.
    
    Returns:
        Dict with collection stats
    """
    try:
        collection = chroma_client.get_collection(name="macro_knowledge")
        count = collection.count()
        
        return {
            "success": True,
            "collection": "macro_knowledge",
            "total_chunks": count,
            "path": CHROMA_DB_PATH
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Run initialize_knowledge_base() first"
        }


# Standalone test
if __name__ == "__main__":
    print("=" * 60)
    print("CHROMADB RAG INITIALIZATION & TEST")
    print("=" * 60)
    
    # Initialize
    print("\n1. Initializing knowledge base...")
    init_result = initialize_knowledge_base()
    print(json.dumps(init_result, indent=2))
    
    if not init_result.get("success"):
        print("\nERROR: Failed to initialize ChromaDB")
        exit(1)
    
    # Get stats
    print("\n2. Collection stats:")
    stats = get_collection_stats()
    print(json.dumps(stats, indent=2))
    
    # Test queries
    test_queries = [
        "India inflation trends",
        "RBI monetary policy",
        "IT sector performance",
        "banking sector outlook"
    ]
    
    print("\n3. Testing queries:\n")
    for query in test_queries:
        print(f"Query: '{query}'")
        results = query_knowledge(query, top_k=2)
        
        for i, chunk in enumerate(results, 1):
            print(f"  Result {i} ({chunk['category']}, relevance: {chunk['relevance']:.2f}):")
            print(f"    {chunk['text'][:100]}...")
        print()
    
    print("=" * 60)
    print("RAG SYSTEM READY")
    print("=" * 60)
