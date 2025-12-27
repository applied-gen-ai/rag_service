"""
RAG Streaming Service with Hybrid Search & Caching
Updated for deploy_rag deployment architecture
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import logging
import json
import os
import asyncio
import time
import traceback
import boto3
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from message_types import status_message, token_message, error_message, done_message, citation_message
from rag_pipeline import RAGPipeline
from llm_client import LLMClient
from conversation_manager import ConversationManager
from utils import MetricsCollector, ValidationError, validate_parameters, validate_query
from cache_manager import CacheManager

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION - deploy_rag compliant
# ============================================================================

# Qdrant Configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "insurance_hybrid_new")
HUGGING_FACE_TOKEN = os.getenv("HUGGING_FACE_TOKEN")

# LLM Configuration (deploy_rag: single endpoint instead of host+port)
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "localhost:50051")

# Server Configuration (deploy_rag: port 8000 for Fargate)
PORT = int(os.getenv("PORT", "8000"))

# Hybrid search configuration
ENABLE_HYBRID_SEARCH = os.getenv("ENABLE_HYBRID_SEARCH", "true").lower() == "true"
ENABLE_RERANKING = os.getenv("ENABLE_RERANKING", "true").lower() == "true"

# Cache configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"

# Global instances
rag_pipeline = None
llm_client = None
cache_manager = None
metrics_collector = MetricsCollector()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def clean_llm_response(response: str) -> str:
    """Clean up LLM response to remove repetition and artifacts"""
    if not response:
        return response
    
    lines = response.split('\n')
    cleaned_lines = [
        line for line in lines
        if not line.strip().startswith('Context:')
    ]
    cleaned = '\n'.join(cleaned_lines)
    
    sentences = [s.strip() for s in cleaned.split('.') if s.strip()]
    unique_sentences = []
    seen = set()
    
    for sentence in sentences:
        normalized = ' '.join(sentence.lower().split())
        if normalized and normalized not in seen and len(normalized) > 5:
            unique_sentences.append(sentence)
            seen.add(normalized)
    
    cleaned = '. '.join(unique_sentences)
    
    if cleaned and not cleaned.endswith('.'):
        cleaned += '.'
    
    return cleaned.strip()


# ============================================================================
# APPLICATION LIFECYCLE
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - handles startup and shutdown"""
    global rag_pipeline, llm_client, cache_manager
    
    logger.info("=" * 80)
    logger.info("Starting RAG Streaming Service (deploy_rag)")
    logger.info("=" * 80)
    
    # Initialize Cache Manager
    if REDIS_ENABLED:
        try:
            logger.info("Initializing cache manager...")
            cache_manager = CacheManager(
                redis_host=REDIS_HOST,
                redis_port=REDIS_PORT,
                default_ttl=3600  # 1 hour default (ttl = time to live)
            )
            if cache_manager.enabled:
                logger.info("Cache manager ready!")
            else:
                logger.warning("Cache manager disabled")
                cache_manager = None
        except Exception as e:
            logger.error(f"Cache manager failed: {str(e)}")
            cache_manager = None
    else:
        logger.info("Redis caching disabled")
    
    # Initialize RAG Pipeline with Hybrid Search & Cache
    if QDRANT_URL and QDRANT_API_KEY:
        try:
            logger.info("Initializing RAG Pipeline...")
            rag_pipeline = RAGPipeline(
                qdrant_url=QDRANT_URL,
                qdrant_api_key=QDRANT_API_KEY,
                collection_name=COLLECTION_NAME,
                hf_token=HUGGING_FACE_TOKEN,
                enable_hybrid_search=ENABLE_HYBRID_SEARCH,
                enable_reranking=ENABLE_RERANKING,
                cache_manager=cache_manager
            )
            stats = rag_pipeline.get_stats()
            logger.info("RAG Pipeline ready!")
            logger.info(f"   Documents: {stats['total_documents']}")
            logger.info(f"   Hybrid Search: {stats['hybrid_search_enabled']}")
            logger.info(f"   BM25 Indexed: {stats.get('bm25_indexed', False)}")
            logger.info(f"   Caching: {stats.get('caching_enabled', False)}")
            
        except Exception as e:
            logger.error(f"RAG Pipeline initialization failed: {str(e)}")
            logger.error(traceback.format_exc())
    else:
        logger.warning("RAG Pipeline not configured (missing QDRANT credentials)")
    
    # Initialize LLM Client (deploy_rag style: single endpoint)
    if LLM_ENDPOINT:
        try:
            logger.info(f"Connecting to LLM service at {LLM_ENDPOINT}...")
            llm_client = LLMClient(llm_endpoint=LLM_ENDPOINT)
            await llm_client.connect()
            logger.info("LLM client connected!")
            
        except Exception as e:
            logger.error(f"LLM connection failed: {str(e)}")
            logger.error(traceback.format_exc())
    else:
        logger.warning("LLM endpoint not configured")
    
    logger.info("=" * 80)
    logger.info("Service startup complete!")
    logger.info(f"   Listening on port {PORT}")
    logger.info("=" * 80)
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("=" * 80)
    logger.info("Shutting down service...")
    logger.info("=" * 80)
    
    if llm_client:
        try:
            await llm_client.close()
            logger.info("LLM client closed")
        except Exception as e:
            logger.error(f"Error closing LLM client: {str(e)}")
    
    logger.info("Shutdown complete")


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="RAG Streaming Service",
    description="Production RAG service with hybrid search, caching, and streaming responses",
    version="1.0.0",
    lifespan=lifespan
)


# ============================================================================
# REST ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with service information"""
    hybrid_status = "enabled" if (rag_pipeline and rag_pipeline.enable_hybrid_search) else "disabled"
    bm25_status = "indexed" if (rag_pipeline and hasattr(rag_pipeline, 'hybrid_engine') and 
                                rag_pipeline.hybrid_engine and rag_pipeline.hybrid_engine.bm25) else "not_indexed"
    cache_status = "enabled" if cache_manager and cache_manager.enabled else "disabled"
    
    return {
        "service": "RAG Streaming Service",
        "version": "1.0.0",
        "status": "healthy",
        "deployment": "aws_fargate",  # deploy_rag identifier
        "components": {
            "rag_pipeline": rag_pipeline is not None,
            "llm_service": llm_client is not None and llm_client.is_connected(),
            "cache": cache_status
        },
        "features": [
            "conversation_history",
            "source_citations",
            "response_cleaning",
            "error_handling",
            "metrics",
            "hybrid_search",
            "reranking",
            "caching"
        ],
        "search_capabilities": {
            "hybrid_search": hybrid_status,
            "bm25": bm25_status,
            "reranking": "enabled" if ENABLE_RERANKING else "disabled"
        },
        "endpoints": {
            "websocket": "/ws/chat",
            "health": "/health",
            "metrics": "/metrics",
            "cache_stats": "/cache/stats"
        }
    }


@app.get("/health")
async def health():
    """
    Comprehensive health check endpoint
    Required for AWS Fargate health checks
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {}
    }
    
    # Check RAG pipeline
    if rag_pipeline:
        try:
            stats = rag_pipeline.get_stats()
            health_status["components"]["rag_pipeline"] = {
                "status": "healthy",
                "details": stats
            }
            
            if hasattr(rag_pipeline, 'qdrant_circuit_breaker'):
                health_status["components"]["rag_pipeline"]["circuit_breaker"] = {
                    "state": rag_pipeline.qdrant_circuit_breaker.state,
                    "failure_count": rag_pipeline.qdrant_circuit_breaker.failure_count
                }
                
        except Exception as e:
            health_status["components"]["rag_pipeline"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
    else:
        health_status["components"]["rag_pipeline"] = {
            "status": "not_initialized"
        }
        health_status["status"] = "unhealthy"
    
    # Check LLM client
    if llm_client and llm_client.is_connected():
        health_status["components"]["llm_client"] = {
            "status": "healthy",
            "endpoint": LLM_ENDPOINT,
            "connected": True
        }
    else:
        health_status["components"]["llm_client"] = {
            "status": "unhealthy",
            "endpoint": LLM_ENDPOINT,
            "connected": False
        }
        health_status["status"] = "degraded"
    
    # Check cache
    if cache_manager:
        cache_stats_data = cache_manager.get_stats()
        health_status["components"]["cache"] = {
            "status": "healthy" if cache_stats_data.get("enabled") else "disabled",
            "stats": cache_stats_data
        }
    else:
        health_status["components"]["cache"] = {
            "status": "not_configured"
        }
    
    # Add metrics summary
    metrics = metrics_collector.get_metrics()
    health_status["metrics_summary"] = {
        "total_queries": metrics["total_queries"],
        "successful_queries": metrics["successful_queries"],
        "failed_queries": metrics["failed_queries"],
        "success_rate": round(
            (metrics["successful_queries"] / metrics["total_queries"] * 100) 
            if metrics["total_queries"] > 0 else 0, 
            2
        ),
        "avg_query_time": round(metrics["avg_query_time"], 2),
        "avg_search_score": round(metrics["avg_search_score"], 3)
    }
    
    return health_status


@app.get("/metrics")
async def get_metrics():
    """Get comprehensive system metrics"""
    metrics = {
        "system": metrics_collector.get_metrics(),
        "timestamp": time.time()
    }
    
    if rag_pipeline and hasattr(rag_pipeline, 'metrics'):
        metrics["rag_pipeline"] = rag_pipeline.metrics.get_metrics()
    
    if rag_pipeline and hasattr(rag_pipeline, 'qdrant_circuit_breaker'):
        metrics["circuit_breakers"] = {
            "qdrant": {
                "state": rag_pipeline.qdrant_circuit_breaker.state,
                "failure_count": rag_pipeline.qdrant_circuit_breaker.failure_count,
                "last_failure_time": rag_pipeline.qdrant_circuit_breaker.last_failure_time
            }
        }
    
    if cache_manager:
        metrics["cache"] = cache_manager.get_stats()
    
    return metrics


@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics"""
    if not cache_manager:
        return {"enabled": False, "status": "not_configured"}
    
    return cache_manager.get_stats()


@app.post("/cache/clear")
async def clear_cache():
    """Clear all cache"""
    if not cache_manager:
        return {"error": "Cache not enabled"}
    
    cache_manager.clear_all()
    return {"status": "success", "message": "Cache cleared"}


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    Main WebSocket endpoint for streaming RAG responses
    
    Message format:
    {
        "query": "What is health insurance?",
        "top_k": 3,
        "max_tokens": 512,
        "temperature": 0.7,
        "show_citations": true,
        "use_hybrid": false,
        "use_reranking": true
    }
    """
    await websocket.accept()
    logger.info("Client connected!")
    
    conversation = ConversationManager(max_turns=5)
    
    try:
        while True:
            start_time = time.time()
            data = await websocket.receive_text()
            
            try:
                # Parse and validate JSON
                try:
                    message = json.loads(data)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON received: {str(e)}")
                    await websocket.send_text(
                        error_message("Invalid JSON format", str(e))
                    )
                    metrics_collector.record_query(success=False)
                    continue
                
                # Extract and validate query
                query = message.get("query", "").strip()
                
                try:
                    validate_query(query)
                except ValidationError as e:
                    logger.warning(f"Query validation failed: {str(e)}")
                    await websocket.send_text(
                        error_message("Invalid query", str(e))
                    )
                    metrics_collector.record_query(success=False)
                    continue
                
                # Extract and validate parameters
                try:
                    params = validate_parameters(
                        top_k=message.get("top_k", 3),
                        max_tokens=message.get("max_tokens", 512),
                        temperature=message.get("temperature", 0.7)
                    )
                except ValidationError as e:
                    logger.warning(f"Parameter validation failed: {str(e)}")
                    await websocket.send_text(
                        error_message("Invalid parameters", str(e))
                    )
                    metrics_collector.record_query(success=False)
                    continue
                
                # Extract search parameters
                show_citations = message.get("show_citations", True)
                use_hybrid = message.get("use_hybrid", False)
                use_reranking = message.get("use_reranking", True)
                
                # Check services availability
                if not rag_pipeline:
                    await websocket.send_text(
                        error_message(
                            "RAG pipeline not initialized",
                            "Server is starting up or configuration is missing"
                        )
                    )
                    metrics_collector.record_query(success=False)
                    continue
                
                if not llm_client or not llm_client.is_connected():
                    await websocket.send_text(
                        error_message(
                            "LLM service unavailable",
                            "The AI model is temporarily unavailable. Please try again."
                        )
                    )
                    metrics_collector.record_query(success=False)
                    metrics_collector.record_error("llm")
                    continue
                
                # Add user message to history
                conversation.add_user_message(query)
                
                # Step 1: Retrieve context (with caching!)
                try:
                    search_method = "hybrid" if use_hybrid else "dense"
                    await websocket.send_text(
                        status_message(f"{'Hybrid' if use_hybrid else 'Dense'} search...")
                    )
                    
                    # This now checks cache automatically
                    context_result = await rag_pipeline.retrieve_context_with_retry(
                        query,
                        top_k=params["top_k"],
                        use_hybrid=use_hybrid,
                        use_reranking=use_reranking
                    )
                        
                except Exception as e:
                    logger.error(f"Context retrieval error: {str(e)}")
                    await websocket.send_text(
                        error_message("Search failed", "Unable to search knowledge base.")
                    )
                    metrics_collector.record_query(success=False)
                    metrics_collector.record_error("qdrant")
                    continue
                
                chunks_found = len(context_result['chunks'])
                best_score = context_result['best_score']
                search_method_used = context_result.get('search_method', 'dense')
                
                # Enhanced status message with search method info
                status_msg = f"Found {chunks_found} relevant chunks (score: {best_score:.3f})"
                if search_method_used == "hybrid":
                    metadata = context_result.get('search_metadata', {})
                    if metadata.get('used_reranking'):
                        status_msg += " [Hybrid + Reranked]"
                    else:
                        status_msg += " [Hybrid]"
                
                await websocket.send_text(status_message(status_msg))
                
                # Step 2: Send citations
                if show_citations and context_result.get('sources'):
                    await websocket.send_text(citation_message(context_result['sources']))
                
                # Step 3: Build prompt
                prompt = rag_pipeline.build_prompt_with_history(
                    query=query,
                    context=context_result["context"],
                    conversation_history=conversation.get_history()
                )
                
                turn_count = conversation.get_turn_count()
                logger.info(f"Built prompt with {turn_count} turns of history")
                logger.info(f"   Search method: {search_method_used}")
                
                # Step 4: Stream from LLM with error handling
                await websocket.send_text(status_message("Generating response..."))
                
                full_response = ""
                token_count = 0
                
                try:
                    async for token in llm_client.stream_generate(
                        prompt=prompt,
                        max_tokens=params["max_tokens"],
                        temperature=params["temperature"]
                    ):
                        await websocket.send_text(token_message(token))
                        full_response += token
                        token_count += 1
                        
                except asyncio.TimeoutError:
                    logger.error("LLM stream timeout")
                    await websocket.send_text(
                        error_message("Response timeout", "Generation took too long.")
                    )
                    metrics_collector.record_query(success=False)
                    metrics_collector.record_error("llm")
                    continue
                    
                except Exception as e:
                    logger.error(f"LLM streaming error: {str(e)}")
                    logger.error(traceback.format_exc())
                    await websocket.send_text(
                        error_message("Generation failed", "Unable to generate response.")
                    )
                    metrics_collector.record_query(success=False)
                    metrics_collector.record_error("llm")
                    continue
                
                # Clean and save response
                cleaned_response = clean_llm_response(full_response.strip())
                conversation.add_assistant_message(cleaned_response)
                
                # Record metrics
                query_time = time.time() - start_time
                metrics_collector.record_query(
                    success=True,
                    query_time=query_time,
                    search_score=best_score,
                    tokens=token_count
                )

                # calling the cloudwatch metrics function
                try:
                    publish_metrics(
                    question=query,
                    answer=cleaned_response,
                    request_time_ms=int(query_time * 1000)
                )
                except Exception as e:
                    logger.error(f"CloudWatch metrics failed: {e}")
                
                # Done
                await websocket.send_text(done_message("Response complete"))
                
                logger.info(f"Query completed in {query_time:.2f}s ({token_count} tokens, {search_method_used} search)")
                
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                logger.error(traceback.format_exc())
                await websocket.send_text(
                    error_message("Unexpected error", "An unexpected error occurred.")
                )
                metrics_collector.record_query(success=False)
            
    except WebSocketDisconnect:
        logger.info(f"Client disconnected (had {conversation.get_turn_count()} turns)")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 80)
    logger.info("Starting RAG Streaming Service in development mode")
    logger.info("=" * 80)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )

# ECS service name (USED FOR CLOUDWATCH DIMENSIONS)
ECS_SERVICE_NAME = os.getenv("ECS_SERVICE_NAME", "rag-service")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

cloudwatch = boto3.client("cloudwatch", region_name=AWS_REGION)

def publish_metrics(question: str, answer: str, request_time_ms: int):
    """
    Publish custom CloudWatch metrics
    """
    cloudwatch.put_metric_data(
        Namespace="CustomApp",
        MetricData=[
            {
                "MetricName": "UsersAskingQuestions",
                "Dimensions": [{"Name": "Service", "Value": ECS_SERVICE_NAME}],
                "Value": 1,
                "Unit": "Count"
            },
            {
                "MetricName": "QuestionsAsked",
                "Dimensions": [{"Name": "Service", "Value": ECS_SERVICE_NAME}],
                "Value": 1,
                "Unit": "Count"
            },
            {
                "MetricName": "AverageQuestionLength",
                "Dimensions": [{"Name": "Service", "Value": ECS_SERVICE_NAME}],
                "Value": len(question),
                "Unit": "Count"
            },
            {
                "MetricName": "AverageAnswerLength",
                "Dimensions": [{"Name": "Service", "Value": ECS_SERVICE_NAME}],
                "Value": len(answer),
                "Unit": "Count"
            },
            {
                "MetricName": "AverageRequestTime",
                "Dimensions": [{"Name": "Service", "Value": ECS_SERVICE_NAME}],
                "Value": request_time_ms,
                "Unit": "Milliseconds"
            }
        ]
    )