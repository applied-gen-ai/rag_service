"""
Embedding module - converts text to vectors using HuggingFace models
WITH caching support for faster repeated queries
"""
import logging
import os
from typing import List
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Wrapper for HuggingFace embedding model with caching"""
    
    def __init__(
        self, 
        model_name: str = "infly/inf-retriever-v1-1.5b",
        hf_token: str = None,
        cache_manager = None  # ← NEW: Optional cache manager
    ):
        """
        Initialize embedding model
        
        Args:
            model_name: HuggingFace model name
            hf_token: HuggingFace API token (required for gated models)
            cache_manager: Optional cache manager for caching embeddings
        """
        logger.info(f"Loading embedding model: {model_name}")
        logger.info("This is a large model (~3GB), first download may take a while...")
        
        self.model_name = model_name
        self.cache_manager = cache_manager  # ← Store cache manager
        
        # Get token from parameter or environment
        token = hf_token or os.getenv("HUGGING_FACE_TOKEN")
        
        if not token:
            logger.warning("No HuggingFace token provided. Model may fail to load.")
        
        # Initialize HuggingFace embeddings
        self.model = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"token": token} if token else {},
            encode_kwargs={"normalize_embeddings": True}  # Normalize for better similarity
        )
        
        logger.info("Embedding model loaded")
        logger.info(f"Model: {model_name}")
        logger.info(f"Expected dimension: 1536")
        
        if cache_manager:
            logger.info("Embedding cache enabled")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Convert text to embedding vector with optional caching
        
        Args:
            text: Input text
            
        Returns:
            List of floats representing the embedding (1536 dimensions)
        """
        # Check cache first
        if self.cache_manager:
            cached_embedding = self.cache_manager.get_embedding(text)
            if cached_embedding is not None:
                logger.debug("Using cached embedding")
                return cached_embedding
        
        # Generate embedding using the query method
        embedding = self.model.embed_query(text)
        
        logger.debug(f"Generated embedding with {len(embedding)} dimensions")
        
        # Cache the result (24 hour TTL)
        if self.cache_manager:
            self.cache_manager.set_embedding(text, embedding, ttl=86400)
            logger.debug("Cached embedding")
        
        return embedding
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Convert multiple texts to embeddings with caching support
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embeddings, each with 1536 dimensions
        """
        embeddings = []
        texts_to_embed = []
        text_indices = []
        
        # Check cache for each text
        if self.cache_manager:
            for i, text in enumerate(texts):
                cached_embedding = self.cache_manager.get_embedding(text)
                if cached_embedding is not None:
                    embeddings.append(cached_embedding)
                    logger.debug(f"Using cached embedding for text {i+1}/{len(texts)}")
                else:
                    # Need to generate this one
                    embeddings.append(None)
                    texts_to_embed.append(text)
                    text_indices.append(i)
        else:
            # No cache, embed all
            texts_to_embed = texts
            text_indices = list(range(len(texts)))
            embeddings = [None] * len(texts)
        
        # Generate embeddings for uncached texts
        if texts_to_embed:
            logger.debug(f"Generating {len(texts_to_embed)} embeddings")
            new_embeddings = self.model.embed_documents(texts_to_embed)
            
            # Place new embeddings in correct positions and cache them
            for i, (text_idx, embedding) in enumerate(zip(text_indices, new_embeddings)):
                embeddings[text_idx] = embedding
                
                # Cache the new embedding
                if self.cache_manager:
                    self.cache_manager.set_embedding(texts_to_embed[i], embedding, ttl=86400)
                    logger.debug(f"Cached embedding {i+1}/{len(texts_to_embed)}")
        
        logger.debug(f"Generated/retrieved {len(embeddings)} embeddings total")
        
        return embeddings