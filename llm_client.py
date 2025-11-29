"""
gRPC client for LLM service on AWS EKS
Connects to vLLM via gRPC and streams tokens

Updated for deploy_rag: Uses single endpoint string parameter
"""
import logging
import os
from typing import AsyncGenerator
import grpc

from llm_grpc import llm_pb2, llm_pb2_grpc

logger = logging.getLogger(__name__)


class LLMClient:
    """Async gRPC client for streaming LLM responses"""
    
    def __init__(self, llm_endpoint: str):
        """
        Initialize LLM client
        
        Args:
            llm_endpoint: LLM service endpoint in format "host:port" 
                         (e.g., "a1b2c3-nlb.elb.us-east-1.amazonaws.com:50051")
                         Can also be set via LLM_ENDPOINT environment variable
        """
        # Parse endpoint string
        if ":" in llm_endpoint:
            self.host, port_str = llm_endpoint.rsplit(":", 1)
            self.port = int(port_str)
        else:
            # Default to port 50051 if not specified
            self.host = llm_endpoint
            self.port = 50051
        
        self.llm_endpoint = f"{self.host}:{self.port}"
        self.channel = None
        self.stub = None
        self._connected = False
        
        logger.info(f"LLM Client initialized with endpoint: {self.llm_endpoint}")
    
    async def connect(self):
        """
        Establish gRPC connection to LLM service
        """
        try:
            logger.info(f"Connecting to LLM service at {self.llm_endpoint}...")
            
            # Create async gRPC channel with optimized settings for AWS
            self.channel = grpc.aio.insecure_channel(
                self.llm_endpoint,
                options=[
                    ('grpc.max_send_message_length', 100 * 1024 * 1024),  # 100MB
                    ('grpc.max_receive_message_length', 100 * 1024 * 1024),  # 100MB
                    ('grpc.keepalive_time_ms', 30000),  # 30 seconds
                    ('grpc.keepalive_timeout_ms', 10000),  # 10 seconds
                    ('grpc.keepalive_permit_without_calls', True),
                    ('grpc.http2.max_pings_without_data', 0),
                ]
            )
            
            # Create stub (the client interface)
            self.stub = llm_pb2_grpc.LLMStub(self.channel)
            
            # Test connection with a simple health check
            await self._health_check()
            
            self._connected = True
            logger.info("Connected to LLM service successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to LLM service: {str(e)}")
            self._connected = False
            raise
    
    async def _health_check(self):
        """
        Simple health check by attempting a minimal generation
        """
        try:
            request = llm_pb2.GenerateRequest(
                prompt="test",
                max_tokens=1,
                temperature=0.0
            )
            
            # Try non-streaming first (faster health check)
            response = await self.stub.Generate(request, timeout=10)
            logger.info("LLM service health check passed")
            
        except grpc.RpcError as e:
            logger.warning(f"Health check failed: {e.code()} - {e.details()}")
            # Don't raise - service might only support streaming
    
    async def stream_generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50
    ) -> AsyncGenerator[str, None]:
        """
        Stream generate tokens from LLM
        
        Args:
            prompt: Input prompt (query + RAG context)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic, 2.0 = random)
            top_p: Top-p (nucleus) sampling
            top_k: Top-k sampling
            
        Yields:
            Generated tokens as strings
        """
        if not self._connected:
            await self.connect()
        
        try:
            # Create request
            request = llm_pb2.GenerateRequest(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k
            )
            
            logger.info(f"Streaming generation request:")
            logger.info(f"   Prompt length: {len(prompt)} chars")
            logger.info(f"   Max tokens: {max_tokens}")
            logger.info(f"   Temperature: {temperature}")
            
            # Stream tokens
            token_count = 0
            async for token_msg in self.stub.StreamGenerate(request):
                if token_msg.text:
                    token_count += 1
                    yield token_msg.text
            
            logger.info(f"Streaming complete - generated {token_count} tokens")
            
        except grpc.RpcError as e:
            logger.error(f"gRPC error during streaming: {e.code()} - {e.details()}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during streaming: {str(e)}")
            raise
    
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50
    ) -> str:
        """
        Generate complete response (non-streaming)
        
        Args:
            prompt: Input prompt (query + RAG context)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling
            top_k: Top-k sampling
            
        Returns:
            Complete generated text
        """
        if not self._connected:
            await self.connect()
        
        try:
            request = llm_pb2.GenerateRequest(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k
            )
            
            logger.info(f"Non-streaming generation request")
            logger.info(f"   Prompt length: {len(prompt)} chars")
            
            response = await self.stub.Generate(request, timeout=60)
            
            logger.info(f"Generation complete: {len(response.text)} chars")
            return response.text
            
        except grpc.RpcError as e:
            logger.error(f"gRPC error: {e.code()} - {e.details()}")
            raise
    
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._connected
    
    async def close(self):
        """Close gRPC connection"""
        if self.channel:
            logger.info("Closing gRPC channel...")
            await self.channel.close()
            self._connected = False
            logger.info("gRPC channel closed")


# Global LLM client instance (initialized from environment variable)
# This follows the deploy_rag pattern for easy import in other modules
def get_llm_client() -> LLMClient:
    """
    Factory function to get LLM client instance
    
    Reads LLM_ENDPOINT from environment variable
    
    Returns:
        LLMClient instance
    """
    llm_endpoint = os.getenv("LLM_ENDPOINT", "localhost:50051")
    return LLMClient(llm_endpoint)


# For convenience, create a global instance
llm_client = get_llm_client()