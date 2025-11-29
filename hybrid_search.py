"""
Hybrid search combining dense vectors and BM25 sparse search
Plus CrossEncoder reranking for improved accuracy
"""
import logging
from typing import List, Dict, Any, Tuple
from rank_bm25 import BM25Okapi
import numpy as np
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class HybridSearchEngine:
    """
    Hybrid search combining dense vector search and BM25 keyword search
    with optional CrossEncoder reranking
    """
    
    def __init__(
        self,
        vector_search_client,
        enable_reranking: bool = True,
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ):
        """
        Initialize hybrid search engine
        
        Args:
            vector_search_client: Qdrant client for dense search
            enable_reranking: Whether to use CrossEncoder reranking
            reranker_model: CrossEncoder model name
        """
        self.vector_search = vector_search_client
        self.enable_reranking = enable_reranking
        
        # Initialize reranker if enabled
        self.reranker = None
        if enable_reranking:
            logger.info(f"Loading reranker model: {reranker_model}")
            try:
                self.reranker = CrossEncoder(reranker_model)
                logger.info("Reranker model loaded")
            except Exception as e:
                logger.error(f"Failed to load reranker: {str(e)}")
                self.enable_reranking = False
        
        # BM25 will be initialized with document corpus
        self.bm25 = None
        self.documents = []
        self.doc_ids = []
        
        logger.info("HybridSearchEngine initialized")
    
    def index_documents(self, documents: List[Dict[str, Any]]):
        """
        Index documents for BM25 search
        
        Args:
            documents: List of document dictionaries with 'id' and 'text'
        """
        logger.info(f"Indexing {len(documents)} documents for BM25...")
        
        self.documents = documents
        self.doc_ids = [doc['id'] for doc in documents]
        
        # Tokenize documents for BM25
        tokenized_corpus = [doc['text'].lower().split() for doc in documents]
        
        # Initialize BM25
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        logger.info(f"Indexed {len(documents)} documents")
    
    def bm25_search(self, query: str, top_k: int = 20) -> List[Tuple[str, float]]:
        """
        Perform BM25 keyword search
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of (doc_id, score) tuples
        """
        if not self.bm25:
            logger.warning("BM25 not initialized, returning empty results")
            return []
        
        # Tokenize query
        tokenized_query = query.lower().split()
        
        # Get BM25 scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top-k results
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = [
            (self.doc_ids[idx], float(scores[idx]))
            for idx in top_indices
            if scores[idx] > 0  # Filter out zero scores
        ]
        
        logger.info(f"BM25 search found {len(results)} results")
        return results
    
    async def dense_search(
        self,
        query_vector: List[float],
        top_k: int = 20,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Perform dense vector search
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            
        Returns:
            List of search results with scores
        """
        results = self.vector_search.search(
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold
        )
        
        logger.info(f"Dense search found {len(results)} results")
        return results
    
    def reciprocal_rank_fusion(
        self,
        dense_results: List[Dict[str, Any]],
        bm25_results: List[Tuple[str, float]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Combine dense and BM25 results using Reciprocal Rank Fusion (RRF)
        
        RRF formula: score(d) = sum(1 / (k + rank(d)))
        
        Args:
            dense_results: Results from dense search
            bm25_results: Results from BM25 search
            k: Constant for RRF (default 60)
            
        Returns:
            Fused and sorted results
        """
        # Create document dictionary for fusion
        fused_scores = {}
        doc_data = {}
        
        # Add dense results
        for rank, result in enumerate(dense_results, 1):
            doc_id = result['id']
            fused_scores[doc_id] = fused_scores.get(doc_id, 0) + (1 / (k + rank))
            if doc_id not in doc_data:
                doc_data[doc_id] = result
        
        # Add BM25 results
        for rank, (doc_id, bm25_score) in enumerate(bm25_results, 1):
            fused_scores[doc_id] = fused_scores.get(doc_id, 0) + (1 / (k + rank))
            # If not in dense results, need to fetch document data
            if doc_id not in doc_data:
                # Find document in self.documents
                for doc in self.documents:
                    if doc['id'] == doc_id:
                        doc_data[doc_id] = {
                            'id': doc_id,
                            'text': doc['text'],
                            'score': 0.0,  # Will be updated with fused score
                            'metadata': doc.get('metadata', {})
                        }
                        break
        
        # Sort by fused score
        sorted_docs = sorted(
            fused_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Create final results
        fused_results = []
        for doc_id, fused_score in sorted_docs:
            if doc_id in doc_data:
                result = doc_data[doc_id].copy()
                result['fused_score'] = fused_score
                result['fusion_method'] = 'RRF'
                fused_results.append(result)
        
        logger.info(f"RRF fusion produced {len(fused_results)} results")
        return fused_results
    
    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Rerank candidates using CrossEncoder
        
        Args:
            query: User query
            candidates: Candidate documents to rerank
            top_k: Number of top results to return
            
        Returns:
            Reranked results
        """
        if not self.enable_reranking or not self.reranker:
            logger.warning("Reranking disabled, returning candidates as-is")
            return candidates[:top_k]
        
        if not candidates:
            return []
        
        # Prepare query-document pairs
        pairs = [[query, doc['text']] for doc in candidates]
        
        # Get reranking scores
        rerank_scores = self.reranker.predict(pairs)
        
        # Add rerank scores to candidates
        for doc, score in zip(candidates, rerank_scores):
            doc['rerank_score'] = float(score)
        
        # Sort by rerank score
        reranked = sorted(
            candidates,
            key=lambda x: x['rerank_score'],
            reverse=True
        )
        
        logger.info(f"Reranked {len(candidates)} candidates, returning top {top_k}")
        return reranked[:top_k]
    
    async def hybrid_search(
        self,
        query: str,
        query_vector: List[float],
        top_k: int = 3,
        use_reranking: bool = True
    ) -> Dict[str, Any]:
        """
        Perform complete hybrid search: Dense + BM25 + Reranking
        
        Args:
            query: User query text
            query_vector: Query embedding vector
            top_k: Final number of results to return
            use_reranking: Whether to apply reranking
            
        Returns:
            Dictionary with search results and metadata
        """
        logger.info(f"Starting hybrid search for: '{query[:50]}...'")
        
        # Step 1: Dense search (get more candidates for fusion)
        dense_results = await self.dense_search(
            query_vector=query_vector,
            top_k=20  # Get more candidates
        )
        
        # Step 2: BM25 search (if indexed)
        bm25_results = []
        if self.bm25:
            bm25_results = self.bm25_search(query, top_k=20)
        
        # Step 3: Fusion
        if bm25_results:
            # Use hybrid fusion
            fused_results = self.reciprocal_rank_fusion(
                dense_results,
                bm25_results,
                k=60
            )
            logger.info("Using hybrid fusion (Dense + BM25)")
        else:
            # Fall back to dense only
            fused_results = dense_results
            logger.info("Using dense search only (BM25 not available)")
        
        # Step 4: Reranking (if enabled)
        if use_reranking and self.enable_reranking:
            # Get top 10 candidates for reranking
            candidates = fused_results[:10]
            final_results = self.rerank(query, candidates, top_k=top_k)
            logger.info("Applied CrossEncoder reranking")
        else:
            final_results = fused_results[:top_k]
            logger.info("Reranking skipped")
        
        return {
            "results": final_results,
            "total_candidates": len(dense_results) + len(bm25_results),
            "after_fusion": len(fused_results),
            "final_count": len(final_results),
            "used_bm25": len(bm25_results) > 0,
            "used_reranking": use_reranking and self.enable_reranking
        }