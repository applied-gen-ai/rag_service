"""
Utility functions for error handling, retries, and monitoring
"""
import asyncio
import logging
import time
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry a function with exponential backoff
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch
        
    Returns:
        Result of the function
        
    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except exceptions as e:
            last_exception = e
            
            if attempt == max_retries:
                logger.error(f"All {max_retries} retries failed: {str(e)}")
                raise
            
            logger.warning(f"Attempt {attempt + 1}/{max_retries + 1} failed: {str(e)}")
            logger.info(f"Retrying in {delay:.1f} seconds...")
            
            await asyncio.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)
    
    raise last_exception


class CircuitBreaker:
    """
    Circuit breaker pattern for external service calls
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        logger.info(f"CircuitBreaker initialized (threshold: {failure_threshold}, timeout: {recovery_timeout}s)")
    
    async def call(self, func: Callable, *args, **kwargs):
        """
        Call function through circuit breaker
        
        Args:
            func: Function to call
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Result of function call
            
        Raises:
            Exception if circuit is open or call fails
        """
        # Check if we should attempt recovery
        if self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                logger.info("Circuit breaker entering HALF_OPEN state")
                self.state = "HALF_OPEN"
            else:
                raise Exception(f"Circuit breaker is OPEN (service unavailable)")
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset circuit breaker
            if self.state == "HALF_OPEN":
                logger.info("Circuit breaker closing (service recovered)")
                self.state = "CLOSED"
                self.failure_count = 0
            
            return result
            
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            logger.warning(f"Circuit breaker failure {self.failure_count}/{self.failure_threshold}: {str(e)}")
            
            # Open circuit if threshold reached
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"Circuit breaker OPENED (too many failures)")
            
            raise


class MetricsCollector:
    """Simple metrics collector for monitoring"""
    
    def __init__(self):
        self.metrics = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "total_tokens_generated": 0,
            "avg_query_time": 0.0,
            "avg_search_score": 0.0,
            "qdrant_errors": 0,
            "llm_errors": 0
        }
        self.query_times = []
        self.search_scores = []
    
    def record_query(self, success: bool, query_time: float = 0.0, search_score: float = 0.0, tokens: int = 0):
        """Record query metrics"""
        self.metrics["total_queries"] += 1
        
        if success:
            self.metrics["successful_queries"] += 1
            self.query_times.append(query_time)
            if search_score > 0:
                self.search_scores.append(search_score)
            self.metrics["total_tokens_generated"] += tokens
        else:
            self.metrics["failed_queries"] += 1
        
        # Update averages
        if self.query_times:
            self.metrics["avg_query_time"] = sum(self.query_times) / len(self.query_times)
        if self.search_scores:
            self.metrics["avg_search_score"] = sum(self.search_scores) / len(self.search_scores)
    
    def record_error(self, error_type: str):
        """Record error by type"""
        key = f"{error_type}_errors"
        if key in self.metrics:
            self.metrics[key] += 1
    
    def get_metrics(self) -> dict:
        """Get all metrics"""
        return self.metrics.copy()
    
    def reset(self):
        """Reset all metrics"""
        self.__init__()



class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def validate_query(query: str, max_length: int = 1000, min_length: int = 1) -> None:
    """
    Validate user query
    
    Args:
        query: User's query string
        max_length: Maximum allowed length
        min_length: Minimum allowed length
        
    Raises:
        ValidationError: If query is invalid
    """
    if not query or not query.strip():
        raise ValidationError("Query cannot be empty")
    
    if len(query) < min_length:
        raise ValidationError(f"Query too short (minimum {min_length} characters)")
    
    if len(query) > max_length:
        raise ValidationError(f"Query too long (maximum {max_length} characters)")
    
    # Check for suspicious patterns
    if query.count('\n') > 20:
        raise ValidationError("Query contains too many line breaks")


def validate_parameters(
    top_k: int = 3,
    max_tokens: int = 512,
    temperature: float = 0.7
) -> dict:
    """
    Validate and sanitize query parameters
    
    Args:
        top_k: Number of chunks to retrieve
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        
    Returns:
        Dictionary of validated parameters
        
    Raises:
        ValidationError: If parameters are invalid
    """
    # Validate top_k
    if not isinstance(top_k, int) or top_k < 1 or top_k > 10:
        raise ValidationError("top_k must be between 1 and 10")
    
    # Validate max_tokens
    if not isinstance(max_tokens, int) or max_tokens < 10 or max_tokens > 2048:
        raise ValidationError("max_tokens must be between 10 and 2048")
    
    # Validate temperature
    if not isinstance(temperature, (int, float)) or temperature < 0.0 or temperature > 2.0:
        raise ValidationError("temperature must be between 0.0 and 2.0")
    
    return {
        "top_k": top_k,
        "max_tokens": max_tokens,
        "temperature": float(temperature)
    }