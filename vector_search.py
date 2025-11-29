"""
Qdrant client for vector search
Configured for insurance_hybrid_new collection with 1536-dim vectors
"""
import logging
from typing import List, Dict, Any
from qdrant_client import QdrantClient as QdrantClientLib
from qdrant_client.models import Distance, PointStruct

logger = logging.getLogger(__name__)


class QdrantClient:
    """Wrapper for Qdrant operations"""
    
    def __init__(
        self, 
        url: str, 
        api_key: str, 
        collection_name: str,
        vector_name: str = "dense"
    ):
        """
        Initialize Qdrant client
        
        Args:
            url: Qdrant instance URL
            api_key: API key for authentication
            collection_name: Name of the collection to use
            vector_name: Name of the vector field (default: "dense")
        """
        logger.info("Connecting to Qdrant...")
        
        self.client = QdrantClientLib(
            url=url,
            api_key=api_key,
            timeout=60,
            prefer_grpc=False  # Use HTTP (more compatible)
        )
        
        self.collection_name = collection_name
        self.vector_name = vector_name
        
        # Test connection
        try:
            collections = self.client.get_collections()
            logger.info(f"Connected to Qdrant")
            logger.info(f"Available collections: {[c.name for c in collections.collections]}")
            
            # Check if our collection exists
            collection_names = [c.name for c in collections.collections]
            if collection_name not in collection_names:
                logger.error(f"Collection '{collection_name}' not found!")
                logger.error(f"Available: {collection_names}")
                raise ValueError(f"Collection {collection_name} does not exist")
            
            # Get collection info
            info = self.client.get_collection(collection_name)
            logger.info(f"Collection '{collection_name}' found")
            logger.info(f"Points count: {info.points_count}")
            
            # Check vector configuration
            if hasattr(info.config.params, 'vectors'):
                if isinstance(info.config.params.vectors, dict):
                    # Named vectors (hybrid setup)
                    if vector_name in info.config.params.vectors:
                        vector_config = info.config.params.vectors[vector_name]
                        logger.info(f"Vector '{vector_name}' size: {vector_config.size}")
                        logger.info(f"Vector distance: {vector_config.distance}")
                        
                        if vector_config.size != 1536:
                            logger.warning(f"Expected 1536 dimensions, found {vector_config.size}")
                    else:
                        logger.error(f"Vector '{vector_name}' not found in collection")
                        logger.error(f"Available vectors: {list(info.config.params.vectors.keys())}")
                else:
                    # Single vector
                    logger.info(f"Vector size: {info.config.params.vectors.size}")
                
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {str(e)}")
            raise
    
    def search(
        self, 
        query_vector: List[float], 
        limit: int = 5,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors using dense retrieval
        
        Args:
            query_vector: The query embedding (1536 dimensions)
            limit: Number of results to return
            score_threshold: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            List of search results with text and metadata
        """
        try:
            # Validate vector dimension
            if len(query_vector) != 1536:
                logger.error(f"Invalid vector dimension: {len(query_vector)}, expected 1536")
                raise ValueError(f"Query vector must be 1536 dimensions, got {len(query_vector)}")
            
            # Search in Qdrant using named vector
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=(self.vector_name, query_vector),  # Use named vector
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True  # Include metadata
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": str(result.id),
                    "score": float(result.score),
                    "text": result.payload.get("text", ""),
                    "metadata": {
                        "source": result.payload.get("source", ""),
                        "context": result.payload.get("context", ""),
                        "policy": result.payload.get("policy", "")
                    }
                })
            
            logger.info(f"Found {len(formatted_results)} results")
            if formatted_results:
                logger.info(f"Best score: {formatted_results[0]['score']:.4f}")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise


    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the collection
        
        Returns:
            Dictionary with collection details
        """
        try:
            info = self.client.get_collection(self.collection_name)
            
            return {
                "name": self.collection_name,
                "points_count": info.points_count,
                "vector_size": info.config.params.vectors.get(self.vector_name).size if isinstance(info.config.params.vectors, dict) else info.config.params.vectors.size,
                "status": info.status
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {str(e)}")
            return {}