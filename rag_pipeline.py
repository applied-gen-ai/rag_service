"""
RAG Pipeline - Retrieval Augmented Generation
WITH hybrid search, error handling, retry logic, circuit breaker, AND caching
"""
import logging
from typing import List, Dict, Any, Optional
from embeddings import EmbeddingModel
from vector_search import QdrantClient
from hybrid_search import HybridSearchEngine
from utils import retry_with_backoff, CircuitBreaker, MetricsCollector, ValidationError, validate_query

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Complete RAG pipeline with hybrid search and caching support"""
    
    def __init__(
        self,
        qdrant_url: str,
        qdrant_api_key: str,
        collection_name: str,
        hf_token: str = None,
        enable_hybrid_search: bool = True,
        enable_reranking: bool = True,
        cache_manager = None  # ← NEW: Optional cache manager
    ):
        """
        Initialize RAG pipeline
        
        Args:
            qdrant_url: Qdrant instance URL
            qdrant_api_key: Qdrant API key
            collection_name: Qdrant collection name
            hf_token: HuggingFace token
            enable_hybrid_search: Enable BM25 + dense fusion
            enable_reranking: Enable CrossEncoder reranking
            cache_manager: Optional cache manager for caching
        """
        logger.info("Initializing RAG Pipeline...")
        logger.info("  Model: infly/inf-retriever-v1-1.5b")
        logger.info("  Dimensions: 1536")
        logger.info(f"  Collection: {collection_name}")
        logger.info(f"  Hybrid Search: {'Enabled' if enable_hybrid_search else 'Disabled'}")
        logger.info(f"  Reranking: {'Enabled' if enable_reranking else 'Disabled'}")
        logger.info(f"  Caching: {'Enabled' if cache_manager else 'Disabled'}")
        
        # Store cache manager
        self.cache_manager = cache_manager
        
        logger.info("Loading embedding model...")
        self.embedding_model = EmbeddingModel(
            hf_token=hf_token,
            cache_manager=cache_manager  # ← Pass cache to embeddings
        )
        
        logger.info("Connecting to Qdrant...")
        self.qdrant_client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            collection_name=collection_name,
            vector_name="dense"
        )
        
        # Initialize circuit breaker for Qdrant protection
        logger.info("Initializing circuit breaker for Qdrant...")
        self.qdrant_circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0,
            expected_exception=Exception
        )
        
        # Initialize metrics collector
        logger.info("Initializing metrics collector...")
        self.metrics = MetricsCollector()
        
        # Initialize hybrid search
        self.enable_hybrid_search = enable_hybrid_search
        self.hybrid_engine = None
        
        if enable_hybrid_search:
            logger.info("Initializing hybrid search engine...")
            try:
                self.hybrid_engine = HybridSearchEngine(
                    vector_search_client=self.qdrant_client,
                    enable_reranking=enable_reranking
                )
                logger.info("Hybrid search engine initialized")
                logger.info("Note: BM25 index not built yet")
                logger.info("Use index_documents_for_bm25() to enable full hybrid search")
            except Exception as e:
                logger.error(f"Failed to initialize hybrid search: {str(e)}")
                self.enable_hybrid_search = False
        
        logger.info("RAG Pipeline initialized successfully")
        logger.info("- Circuit breaker: CLOSED")
        logger.info("- Metrics collection: ENABLED")
        if cache_manager:
            logger.info("- Cache: ENABLED")
    
    def index_documents_for_bm25(self, documents: List[Dict[str, Any]]):
        """
        Index documents for BM25 search
        
        Args:
            documents: List of documents with 'id' and 'text' fields
        """
        if self.hybrid_engine:
            self.hybrid_engine.index_documents(documents)
            logger.info(f"Indexed {len(documents)} documents for BM25")
        else:
            logger.warning("Hybrid search not enabled, cannot index documents")
    
    def _clean_text(self, text: str) -> str:
        """Clean text artifacts"""
        cleaned = text
        
        # Remove "Context:" lines
        cleaned = '\n'.join([
            line for line in cleaned.split('\n') 
            if not line.strip().startswith('Context:')
        ])
        
        # Remove markdown code blocks
        cleaned = cleaned.replace('```', '')
        
        # Remove "Sure, here's the extracted text:" patterns
        cleaned = cleaned.replace("Sure, here's the extracted text:", "")
        cleaned = cleaned.replace("Sure! Here is the extracted text:", "")
        
        # Remove excessive dashes/separators
        cleaned = cleaned.replace('---', '')
        cleaned = cleaned.replace('–', '-')
        
        # Remove "Def." lines
        cleaned = '\n'.join([
            line for line in cleaned.split('\n')
            if line.strip() not in ['Def.', 'Def']
        ])
        
        # Remove "Optima Restore – Policy Wordings" header
        cleaned = cleaned.replace('Optima Restore – Policy Wordings', '')
        cleaned = cleaned.replace('Optima Restore - Policy Wordings', '')
        cleaned = cleaned.replace('Optima Restore Policy Wordings', '')
        
        # Clean up extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        return cleaned
    
    async def retrieve_context(
        self, 
        query: str, 
        top_k: int = 3,
        score_threshold: float = 0.0
    ) -> Dict[str, Any]:
        """
        Retrieve relevant context for a query with aggressive cleaning
        
        Args:
            query: User's question
            top_k: Number of chunks to retrieve
            score_threshold: Minimum similarity score (0.0 to 1.0)
            
        Returns:
            Dictionary with context and metadata
        """
        logger.info(f"Processing query: '{query[:100]}...'")
        
        # Step 1: Convert query to embedding
        logger.info("  Step 1: Generating query embedding (1536 dims)...")
        query_vector = self.embedding_model.embed_text(query)
        logger.info(f"  Query embedded ({len(query_vector)} dimensions)")
        
        if len(query_vector) != 1536:
            raise ValueError(f"Unexpected embedding dimension: {len(query_vector)}, expected 1536")
        
        # Step 2: Search Qdrant
        logger.info(f"  Step 2: Searching Qdrant (top_k={top_k})...")
        results = self.qdrant_client.search(
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold
        )
        logger.info(f"  Found {len(results)} relevant chunks")
        
        if results:
            logger.info(f"  Best match score: {results[0]['score']:.4f}")
        
        # Step 3: Format context with AGGRESSIVE cleaning
        if not results:
            logger.warning("  No results found for query")
            return {
                "context": "",
                "chunks": [],
                "sources": [],
                "best_score": 0.0,
                "search_method": "dense"
            }
        
        # Build clean context string with aggressive filtering
        context_parts = []
        sources = []
        
        for i, result in enumerate(results, 1):
            text = result['text'].strip()
            
            if text:
                # Apply cleaning
                cleaned_text = self._clean_text(text)
                
                # Only add if there's meaningful content left
                if len(cleaned_text) > 20:
                    context_parts.append(cleaned_text)
                    
                    # Build source info for citations
                    sources.append({
                        "chunk_id": i,
                        "score": result['score'],
                        "score_type": "dense",
                        "text_preview": cleaned_text[:100] + "..." if len(cleaned_text) > 100 else cleaned_text,
                        "metadata": result['metadata']
                    })
        
        context = "\n\n".join(context_parts)
        
        return {
            "context": context,
            "chunks": results,
            "sources": sources,
            "best_score": results[0]["score"] if results else 0.0,
            "search_method": "dense"
        }
    
    async def retrieve_context_hybrid(
        self,
        query: str,
        top_k: int = 3,
        use_reranking: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve context using hybrid search (Dense + BM25 + Reranking)
        
        Args:
            query: User's question
            top_k: Number of final results
            use_reranking: Whether to apply CrossEncoder reranking
            
        Returns:
            Dictionary with context and metadata
        """
        if not self.hybrid_engine:
            logger.warning("Hybrid search not available, falling back to dense search")
            return await self.retrieve_context(query, top_k=top_k)
        
        logger.info(f"Hybrid search for: '{query[:100]}...'")
        
        # Validate query
        validate_query(query)
        
        # Step 1: Generate query embedding
        logger.info("  Step 1: Generating query embedding...")
        query_vector = self.embedding_model.embed_text(query)
        
        if len(query_vector) != 1536:
            raise ValueError(f"Unexpected embedding dimension: {len(query_vector)}")
        
        # Step 2: Hybrid search
        logger.info("  Step 2: Performing hybrid search (Dense + BM25 + Reranking)...")
        search_result = await self.hybrid_engine.hybrid_search(
            query=query,
            query_vector=query_vector,
            top_k=top_k,
            use_reranking=use_reranking
        )
        
        results = search_result['results']
        
        logger.info(f"  Hybrid search complete:")
        logger.info(f"  Total candidates: {search_result['total_candidates']}")
        logger.info(f"  After fusion: {search_result['after_fusion']}")
        logger.info(f"  Final results: {search_result['final_count']}")
        logger.info(f"  Used BM25: {search_result['used_bm25']}")
        logger.info(f"  Used reranking: {search_result['used_reranking']}")
        
        # Step 3: Format context with cleaning
        if not results:
            return {
                "context": "",
                "chunks": [],
                "sources": [],
                "best_score": 0.0,
                "search_method": "hybrid",
                "search_metadata": search_result
            }
        
        # Build clean context
        context_parts = []
        sources = []
        
        for i, result in enumerate(results, 1):
            text = result.get('text', '').strip()
            
            if text:
                # Apply cleaning
                cleaned_text = self._clean_text(text)
                
                if len(cleaned_text) > 20:
                    context_parts.append(cleaned_text)
                    
                    # Get best score (rerank > fused > original)
                    score = result.get('rerank_score', 
                            result.get('fused_score',
                            result.get('score', 0.0)))
                    
                    score_type = "rerank" if 'rerank_score' in result else \
                                "fused" if 'fused_score' in result else "dense"
                    
                    sources.append({
                        "chunk_id": i,
                        "score": float(score),
                        "score_type": score_type,
                        "text_preview": cleaned_text[:100] + "..." if len(cleaned_text) > 100 else cleaned_text,
                        "metadata": result.get('metadata', {})
                    })
        
        context = "\n\n".join(context_parts)
        best_score = sources[0]['score'] if sources else 0.0
        
        return {
            "context": context,
            "chunks": results,
            "sources": sources,
            "best_score": best_score,
            "search_method": "hybrid",
            "search_metadata": search_result
        }
    
    async def retrieve_context_with_retry(
        self,
        query: str,
        top_k: int = 3,
        score_threshold: float = 0.0,
        use_hybrid: bool = False,
        use_reranking: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve context with retry logic, circuit breaker, AND caching
        
        This is the production-ready version with full caching support.
        
        Args:
            query: User's question
            top_k: Number of chunks to retrieve
            score_threshold: Minimum similarity score (only for dense search)
            use_hybrid: Use hybrid search (Dense + BM25 + Reranking)
            use_reranking: Apply reranking (only for hybrid search)
            
        Returns:
            Dictionary with context and metadata
            
        Raises:
            ValidationError: If query is invalid
            Exception: If retrieval fails after all retries
        """
        # Validate query before processing
        try:
            validate_query(query)
        except ValidationError as e:
            logger.error(f"Query validation failed: {str(e)}")
            raise
        
        # Check cache first
        search_type = "hybrid" if use_hybrid else "dense"
        if self.cache_manager:
            cached_result = self.cache_manager.get_search_results(
                query=query,
                top_k=top_k,
                search_type=search_type
            )
            if cached_result:
                logger.info(f"Using cached {search_type} search results")
                return cached_result
        
        # Choose search method
        if use_hybrid and self.hybrid_engine:
            async def _retrieve():
                return await self.qdrant_circuit_breaker.call(
                    self.retrieve_context_hybrid,
                    query,
                    top_k,
                    use_reranking
                )
            search_method = "hybrid"
        else:
            async def _retrieve():
                return await self.qdrant_circuit_breaker.call(
                    self.retrieve_context,
                    query,
                    top_k,
                    score_threshold
                )
            search_method = "dense"
        
        # Retry with exponential backoff
        try:
            logger.info(f"Starting {search_method} retrieval with retry (max 3 attempts)")
            
            result = await retry_with_backoff(
                _retrieve,
                max_retries=3,
                initial_delay=1.0,
                max_delay=10.0,
                backoff_factor=2.0,
                exceptions=(Exception,)
            )
            
            # Cache the result
            if self.cache_manager:
                self.cache_manager.set_search_results(
                    query=query,
                    top_k=top_k,
                    search_type=search_type,
                    results=result,
                    ttl=3600  # Cache for 1 hour
                )
                logger.info(f"Cached {search_type} search results")
            
            logger.info(f"{search_method.capitalize()} retrieval successful")
            return result
            
        except Exception as e:
            logger.error(f"Context retrieval failed after all retries: {str(e)}")
            self.metrics.record_error("qdrant")
            raise
    
    def build_prompt(self, query: str, context: str) -> str:
        """Build basic prompt (without history)"""
        if not context:
            prompt = f"""Answer the following question:

Question: {query}

Answer:"""
        else:
            prompt = f"""You are a helpful insurance policy assistant. Answer using ONLY the context below.

CRITICAL INSTRUCTIONS:
1. Give ONE short answer - maximum 2-3 sentences
2. DO NOT repeat yourself - say each fact ONCE only
3. Use ONLY information from the Context below
4. DO NOT show "Context:" labels or chunk markers
5. If not in context, say "This information is not available"
6. Be direct and factual

Context from policy documents:
{context}

Question: {query}

Answer (2-3 sentences):"""
        
        return prompt
    
    def build_prompt_with_history(
        self, 
        query: str, 
        context: str, 
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """
        Build enhanced prompt with context AND conversation history
        
        Args:
            query: Current user question
            context: Retrieved context chunks
            conversation_history: Previous conversation turns
            
        Returns:
            Complete prompt string for LLM
        """
        if not context:
            prompt = f"""Answer the following question:

Question: {query}

Answer:"""
        else:
            # Build conversation history section
            history_text = ""
            if conversation_history and len(conversation_history) > 0:
                history_text = "\n\nPrevious Conversation:\n"
                for msg in conversation_history:
                    role = "User" if msg["role"] == "user" else "Assistant"
                    content = msg['content'][:200] if len(msg['content']) > 200 else msg['content']
                    history_text += f"{role}: {content}\n"
            
            # ULTRA-STRICT prompt to prevent repetition and hallucination
            prompt = f"""You are a helpful insurance policy assistant. Answer the user's question using ONLY the information in the Context below.

CRITICAL INSTRUCTIONS - FOLLOW EXACTLY:
1. READ the context carefully and extract ONLY the relevant facts
2. Give ONE short answer - maximum 2-3 sentences
3. DO NOT repeat yourself - say each fact ONCE only
4. DO NOT copy text from context - paraphrase in your own words
5. DO NOT show "Context:" labels or chunk markers
6. DO NOT make up information - if not in context, say "This information is not available in the policy documents"
7. DO NOT hallucinate or add external knowledge
8. Be direct and factual - no filler words
9. Consider the conversation history to understand follow-up questions

Context from policy documents:
{context}
{history_text}
Current Question: {query}

Answer (2-3 sentences maximum):"""
        
        return prompt
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics including cache stats"""
        collection_info = self.qdrant_client.get_collection_info()
        
        stats = {
            "embedding_model": "infly/inf-retriever-v1-1.5b",
            "embedding_dimension": 1536,
            "collection": collection_info.get("name", "unknown"),
            "total_documents": collection_info.get("points_count", 0),
            "vector_name": "dense",
            "circuit_breaker_state": self.qdrant_circuit_breaker.state,
            "circuit_breaker_failures": self.qdrant_circuit_breaker.failure_count,
            "hybrid_search_enabled": self.enable_hybrid_search,
            "hybrid_search_available": self.hybrid_engine is not None,
            "caching_enabled": self.cache_manager is not None
        }
        
        # Add BM25 status if hybrid search is available
        if self.hybrid_engine:
            stats["bm25_indexed"] = self.hybrid_engine.bm25 is not None
            stats["bm25_document_count"] = len(self.hybrid_engine.documents) if self.hybrid_engine.bm25 else 0
        
        # Add cache stats if available
        if self.cache_manager:
            stats["cache_stats"] = self.cache_manager.get_stats()
        
        return stats