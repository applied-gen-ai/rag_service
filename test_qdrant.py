"""
Test Qdrant connection and search with infly embeddings
"""
import os
from dotenv import load_dotenv
from vector_search import QdrantClient
from embeddings import EmbeddingModel

load_dotenv()


def test_qdrant():
    print("="*60)
    print("Testing Qdrant Connection")
    print("="*60)
    
    # Get credentials
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    collection = os.getenv("COLLECTION_NAME", "insurance_hybrid_new")
    hf_token = os.getenv("HUGGING_FACE_TOKEN")
    
    if not url or not api_key:
        print("Missing QDRANT_URL or QDRANT_API_KEY in .env")
        return
    
    if not hf_token:
        print("HUGGING_FACE_TOKEN not set - embedding model may fail")
    
    print(f"\nQdrant URL: {url}")
    print(f"Collection: {collection}\n")
    
    # Connect to Qdrant
    print("Connecting to Qdrant...")
    try:
        client = QdrantClient(
            url=url, 
            api_key=api_key, 
            collection_name=collection,
            vector_name="dense"  # Use dense vector
        )
        print("Qdrant connection successful!\n")
        
        # Get collection info
        info = client.get_collection_info()
        print("Collection Info:")
        print(f"  Name: {info['name']}")
        print(f"  Points: {info['points_count']}")
        print(f"  Vector size: {info.get('vector_size', 'N/A')}")
        print()
        
    except Exception as e:
        print(f"Qdrant connection failed: {str(e)}")
        return
    
    # Load embedding model
    print("="*60)
    print("Loading Embedding Model")
    print("="*60)
    
    print("\nModel: infly/inf-retriever-v1-1.5b")
    print("Dimensions: 1536")
    print("Loading...")
    
    try:
        model = EmbeddingModel()
        
        # Verify dimension
        test_vec = model.embed_text("test")
        print(f"Model loaded successfully")
        print(f"   Output dimension: {len(test_vec)}")
        print()
        
    except Exception as e:
        print(f"Model loading failed: {str(e)}")
        return
    
    # Test search
    print("="*60)
    print("Testing Vector Search")
    print("="*60)
    
    # Test query
    query = "What is covered under the insurance policy?"
    print(f"\nQuery: {query}")
    
    # Convert to vector
    print("Converting query to embedding...")
    query_vector = model.embed_text(query)
    print(f"Query embedded ({len(query_vector)} dimensions)")
    
    # Search
    print("\nSearching Qdrant...")
    try:
        results = client.search(query_vector, limit=3)
        
        print(f"Search complete! Found {len(results)} results\n")
        
        # Display results
        print("="*60)
        print("Search Results")
        print("="*60)
        
        for i, result in enumerate(results, 1):
            print(f"\nResult {i}:")
            print(f"   Score: {result['score']:.4f}")
            print(f"   Context: {result['metadata'].get('context', 'N/A')}")
            print(f"   Policy: {result['metadata'].get('policy', 'N/A')}")
            print(f"   Text: {result['text'][:200]}...")
            
    except Exception as e:
        print(f"Search failed: {str(e)}")
        return
    
    print("\n" + "="*60)
    print("All tests passed!")
    print("="*60)


if __name__ == "__main__":
    test_qdrant()