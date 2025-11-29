"""
Index Qdrant documents for BM25 search
Enables full hybrid search capabilities
"""
import asyncio
import os
from dotenv import load_dotenv
from rag_pipeline import RAGPipeline
from qdrant_client import QdrantClient as QdrantClientSDK

load_dotenv()


async def fetch_all_documents():
    """Fetch all documents from Qdrant"""
    print("Fetching documents from Qdrant...")
    
    client = QdrantClientSDK(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    
    collection_name = os.getenv("COLLECTION_NAME", "insurance_hybrid_new")
    
    # Scroll through all points
    offset = None
    all_documents = []
    
    while True:
        result = client.scroll(
            collection_name=collection_name,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False  # Don't need vectors, just text
        )
        
        points, offset = result
        
        for point in points:
            # Extract text from payload
            text = point.payload.get('text', '')
            if text:
                all_documents.append({
                    'id': str(point.id),
                    'text': text,
                    'metadata': point.payload.get('metadata', {})
                })
        
        print(f"  Fetched {len(all_documents)} documents so far...")
        
        if offset is None:
            break
    
    print(f"Fetched {len(all_documents)} total documents\n")
    return all_documents


async def index_for_bm25():
    """Index documents for BM25 search"""
    # Fetch documents
    documents = await fetch_all_documents()
    
    if not documents:
        print("No documents found!")
        return
    
    # Initialize RAG pipeline
    print("Initializing RAG Pipeline...")
    pipeline = RAGPipeline(
        qdrant_url=os.getenv("QDRANT_URL"),
        qdrant_api_key=os.getenv("QDRANT_API_KEY"),
        collection_name=os.getenv("COLLECTION_NAME", "insurance_hybrid_new"),
        hf_token=os.getenv("HUGGING_FACE_TOKEN"),
        enable_hybrid_search=True,
        enable_reranking=True
    )
    
    # Index for BM25
    print("\nIndexing documents for BM25...")
    pipeline.index_documents_for_bm25(documents)
    
    print("BM25 indexing complete!")
    print(f"   Total documents indexed: {len(documents)}\n")
    
    # Test queries
    test_queries = [
        "What is the grace period?",
        "What is covered under hospitalization?",
        "How much is the ambulance cover?",
        "What is the restore benefit?"
    ]
    
    print("=" * 70)
    print("TESTING: Dense-only vs Hybrid Search Comparison")
    print("=" * 70)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 70)
        
        # Test 1: Dense-only search
        print("Method 1: Dense Search (Semantic only)")
        dense_result = await pipeline.retrieve_context(query, top_k=3)
        print(f"   Best score: {dense_result['best_score']:.3f}")
        if dense_result['sources']:
            print(f"   Top result: {dense_result['sources'][0]['text_preview'][:80]}...")
        
        # Test 2: Hybrid search
        print("\nMethod 2: Hybrid Search (Dense + BM25 + Reranking)")
        hybrid_result = await pipeline.retrieve_context_hybrid(
            query=query,
            top_k=3,
            use_reranking=True
        )
        print(f"   Best score: {hybrid_result['best_score']:.3f}")
        print(f"   Score type: {hybrid_result['sources'][0]['score_type'] if hybrid_result['sources'] else 'N/A'}")
        print(f"   Used BM25: {hybrid_result['search_metadata']['used_bm25']}")
        print(f"   Used reranking: {hybrid_result['search_metadata']['used_reranking']}")
        if hybrid_result['sources']:
            print(f"   Top result: {hybrid_result['sources'][0]['text_preview'][:80]}...")
        
        # Compare
        improvement = ((hybrid_result['best_score'] - dense_result['best_score']) 
                      / dense_result['best_score'] * 100)
        if improvement > 0:
            print(f"\n   Improvement: +{improvement:.1f}% with hybrid search!")
        else:
            print(f"\n   Difference: {improvement:.1f}%")
    
    print("\n" + "=" * 70)
    print("Testing complete!")
    print("=" * 70)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("BM25 Indexing for Hybrid Search")
    print("=" * 70 + "\n")
    asyncio.run(index_for_bm25())