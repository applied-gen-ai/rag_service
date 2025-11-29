"""
Test the embedding model with infly/inf-retriever-v1-1.5b
"""
import os
from dotenv import load_dotenv
from embeddings import EmbeddingModel

# Load environment variables
load_dotenv()


def test_embedding():
    print("="*60)
    print("Testing Embedding Model: infly/inf-retriever-v1-1.5b")
    print("="*60)
    
    # Get HuggingFace token
    hf_token = os.getenv("HUGGING_FACE_TOKEN")
    if not hf_token:
        print("HUGGING_FACE_TOKEN not found in .env")
        print("Please add your HuggingFace token to .env file")
        return
    
    print("\nLoading model (this may take a while on first run)...")
    model = EmbeddingModel(hf_token=hf_token)
    
    # Test text
    text = "The insurance policy covers medical expenses"
    
    print(f"\nText: {text}")
    print("Generating embedding...")
    
    embedding = model.embed_text(text)
    
    print(f"Embedding generated!")
    print(f"Dimension: {len(embedding)} (should be 1536)")
    print(f"First 10 values: {[f'{x:.4f}' for x in embedding[:10]]}")
    print(f"Value range: [{min(embedding):.4f}, {max(embedding):.4f}]")
    
    # Verify dimension
    if len(embedding) == 1536:
        print("\nCorrect dimension! (1536)")
    else:
        print(f"\nUnexpected dimension: {len(embedding)} (expected 1536)")
    
    # Test similarity
    print("\n" + "="*60)
    print("Testing semantic similarity:")
    print("="*60)
    
    texts = [
        "The policy covers medical expenses",
        "Insurance includes healthcare costs",  # Similar!
        "Cat sits on the mat"  # Different!
    ]
    
    print("\nGenerating embeddings for 3 texts...")
    embeddings = model.embed_batch(texts)
    
    # Calculate cosine similarity
    import numpy as np
    
    def cosine_similarity(a, b):
        """Calculate cosine similarity between two vectors"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    vec1 = np.array(embeddings[0])
    vec2 = np.array(embeddings[1])
    vec3 = np.array(embeddings[2])
    
    sim_1_2 = cosine_similarity(vec1, vec2)
    sim_1_3 = cosine_similarity(vec1, vec3)
    
    print(f"\nText 1: '{texts[0]}'")
    print(f"Text 2: '{texts[1]}'")
    print(f"Similarity: {sim_1_2:.4f} (should be HIGH)")
    
    print(f"\nText 1: '{texts[0]}'")
    print(f"Text 3: '{texts[2]}'")
    print(f"Similarity: {sim_1_3:.4f} (should be LOW)")
    
    # Interpretation
    print("\n" + "="*60)
    print("Interpretation:")
    print("="*60)
    
    if sim_1_2 > 0.7:
        print(f"High similarity between insurance texts: {sim_1_2:.4f}")
    else:
        print(f"Lower than expected: {sim_1_2:.4f}")
    
    if sim_1_3 < 0.5:
        print(f"Low similarity with unrelated text: {sim_1_3:.4f}")
    else:
        print(f"Higher than expected: {sim_1_3:.4f}")


if __name__ == "__main__":
    test_embedding()