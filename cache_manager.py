"""
Redis-based caching for RAG pipeline
Caches: embeddings, search results, and LLM responses
"""
import json
import hashlib
import logging
from typing import Any, Optional, List
import redis
from datetime import timedelta

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages Redis cache for embeddings, search results, and responses"""
    
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        default_ttl: int = 3600  # 1 hour default
    ):
        """
        Initialize cache manager
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            default_ttl: Default time-to-live in seconds
        """
        self.default_ttl = default_ttl
        
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=False,  # We'll handle encoding/decoding
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            logger.info(f"Cache manager connected to Redis at {redis_host}:{redis_port}")
            
        except Exception as e:
            logger.warning(f"Redis not available: {str(e)}")
            logger.warning("   Caching disabled - all operations will bypass cache")
            self.redis_client = None
            self.enabled = False
    
    def _generate_key(self, prefix: str, *args) -> str:
        """
        Generate cache key from prefix and arguments
        
        Args:
            prefix: Key prefix (e.g., 'embedding', 'search', 'response')
            *args: Arguments to hash
            
        Returns:
            Cache key string
        """
        # Create a unique hash from arguments
        content = json.dumps(args, sort_keys=True)
        hash_value = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_value}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if not self.enabled:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache MISS: {key}")
                return None
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = default)
        """
        if not self.enabled:
            return
        
        try:
            serialized = json.dumps(value)
            ttl = ttl or self.default_ttl
            self.redis_client.setex(key, ttl, serialized)
            logger.debug(f"Cached: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
    
    def delete(self, key: str):
        """Delete key from cache"""
        if not self.enabled:
            return
        
        try:
            self.redis_client.delete(key)
            logger.debug(f"Deleted: {key}")
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
    
    def clear_all(self):
        """Clear all cache"""
        if not self.enabled:
            return
        
        try:
            self.redis_client.flushdb()
            logger.info("Cleared all cache")
        except Exception as e:
            logger.error(f"Cache clear error: {str(e)}")
    
    # Specific cache methods
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding"""
        key = self._generate_key("embedding", text)
        return self.get(key)
    
    def set_embedding(self, text: str, embedding: List[float], ttl: int = 86400):
        """
        Cache embedding (24 hour TTL by default)
        
        Args:
            text: Input text
            embedding: Embedding vector
            ttl: Time-to-live (default 24 hours)
        """
        key = self._generate_key("embedding", text)
        self.set(key, embedding, ttl)
    
    def get_search_results(
        self,
        query: str,
        top_k: int,
        search_type: str = "dense"
    ) -> Optional[dict]:
        """Get cached search results"""
        key = self._generate_key("search", query, top_k, search_type)
        return self.get(key)
    
    def set_search_results(
        self,
        query: str,
        top_k: int,
        search_type: str,
        results: dict,
        ttl: int = 3600
    ):
        """
        Cache search results (1 hour TTL by default)
        
        Args:
            query: Search query
            top_k: Number of results
            search_type: Type of search (dense, hybrid)
            results: Search results
            ttl: Time-to-live (default 1 hour)
        """
        key = self._generate_key("search", query, top_k, search_type)
        self.set(key, results, ttl)
    
    def get_response(
        self,
        query: str,
        context: str,
        temperature: float
    ) -> Optional[str]:
        """Get cached LLM response"""
        key = self._generate_key("response", query, context[:500], temperature)
        return self.get(key)
    
    def set_response(
        self,
        query: str,
        context: str,
        temperature: float,
        response: str,
        ttl: int = 1800
    ):
        """
        Cache LLM response (30 minute TTL by default)
        
        Args:
            query: User query
            context: Retrieved context
            temperature: LLM temperature
            response: Generated response
            ttl: Time-to-live (default 30 minutes)
        """
        key = self._generate_key("response", query, context[:500], temperature)
        self.set(key, response, ttl)
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        if not self.enabled:
            return {
                "enabled": False,
                "status": "disabled"
            }
        
        try:
            info = self.redis_client.info()
            return {
                "enabled": True,
                "status": "connected",
                "total_keys": self.redis_client.dbsize(),
                "memory_used": info.get('used_memory_human', 'N/A'),
                "hits": info.get('keyspace_hits', 0),
                "misses": info.get('keyspace_misses', 0),
                "hit_rate": round(
                    info.get('keyspace_hits', 0) / 
                    max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1) * 100,
                    2
                )
            }
        except Exception as e:
            return {
                "enabled": False,
                "status": "error",
                "error": str(e)
            }