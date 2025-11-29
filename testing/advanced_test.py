"""
Advanced RAG Service Test - WebSocket Streaming
Auto-detects ALB URL from Terraform output
Tests RAG service with streaming response from EKS LLM
"""

import asyncio
import websockets
import json
import sys
import subprocess
import time
from datetime import datetime

# ============================================================================
# Auto-detect WebSocket URL from Terraform
# ============================================================================

def get_websocket_url():
    """Get WebSocket URL from terraform output"""
    try:
        result = subprocess.run(
            ["terraform", "output", "-raw", "websocket_url"],
            capture_output=True,
            text=True,
            check=True
        )
        url = result.stdout.strip()
        if url and url.startswith("ws://"):
            return url
        else:
            print("✗ Invalid URL from terraform output")
            return None
    except subprocess.CalledProcessError:
        print("✗ Could not get URL from terraform output")
        print("  Make sure you're in the terraform directory")
        return None
    except FileNotFoundError:
        print("✗ Terraform not found in PATH")
        return None

# ============================================================================
# Main Test Function
# ============================================================================

async def test_rag_streaming(websocket_url, query_text):
    """
    Send a query and receive streaming response
    
    Args:
        websocket_url: WebSocket endpoint URL
        query_text: Question to ask
    """
    
    print("=" * 80)
    print("RAG SERVICE - STREAMING TEST")
    print("=" * 80)
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Endpoint:  {websocket_url}")
    print(f"Query:     {query_text}\n")
    
    start_time = time.time()
    
    try:
        # Connect to WebSocket
        print("Connecting to RAG service...", end=" ", flush=True)
        async with websockets.connect(websocket_url, ping_interval=20) as websocket:
            print("✓ Connected!\n")
            
            # Prepare query
            query = {
                "query": query_text,
                "stream": True
            }
            
            # Send query
            await websocket.send(json.dumps(query))
            print("-" * 80)
            print("STREAMING RESPONSE:")
            print("-" * 80)
            
            # Track response
            full_response = ""
            context_chunks = []
            token_count = 0
            first_token_time = None
            
            # Receive streaming response
            async for message in websocket:
                data = json.loads(message)  # Fixed typo
                
                if data.get("type") == "token":
                    # First token timing
                    if first_token_time is None:
                        first_token_time = time.time()
                        ttft = first_token_time - start_time
                        print(f"\n[Time to First Token: {ttft:.2f}s]\n")
                    
                    # Stream token
                    token = data["content"]
                    print(token, end="", flush=True)
                    full_response += token
                    token_count += 1
                    
                elif data.get("type") == "context":
                    # Context from Qdrant
                    chunks = data.get("chunks", [])
                    context_chunks = chunks
                    print(f"\n[Retrieved {len(chunks)} context chunks from Qdrant]\n")
                    
                elif data.get("type") == "done":
                    # Streaming complete
                    end_time = time.time()
                    total_time = end_time - start_time
                    
                    print("\n")
                    print("-" * 80)
                    print("✓ STREAM COMPLETE")
                    print("-" * 80)
                    
                    # Show statistics
                    print(f"\nStatistics:")
                    print(f"  • Total tokens:        {token_count}")
                    print(f"  • Total time:          {total_time:.2f}s")
                    
                    if first_token_time:
                        print(f"  • Time to first token: {(first_token_time - start_time):.2f}s")
                        streaming_time = end_time - first_token_time
                        if streaming_time > 0:
                            tokens_per_sec = token_count / streaming_time
                            print(f"  • Tokens per second:   {tokens_per_sec:.2f}")
                    
                    print(f"  • Context chunks:      {len(context_chunks)}")
                    
                    # Show metadata from server
                    if "metadata" in data:
                        meta = data["metadata"]
                        print(f"\nServer Metadata:")
                        for key, value in meta.items():
                            print(f"  • {key}: {value}")
                    
                    # Show context sources
                    if context_chunks:
                        print(f"\nContext Sources:")
                        for i, chunk in enumerate(context_chunks[:3], 1):  # Show first 3
                            print(f"  {i}. Score: {chunk.get('score', 'N/A'):.4f}")
                            text_preview = chunk.get('text', '')[:100]
                            print(f"     Preview: {text_preview}...")
                    
                    break
                    
                elif data.get("type") == "error":
                    # Error occurred
                    print(f"\n\n✗ Error from server: {data.get('message', 'Unknown error')}")
                    if "details" in data:
                        print(f"   Details: {data['details']}")
                    break
            
            print("\n" + "=" * 80)
            print("TEST COMPLETED SUCCESSFULLY")
            print("=" * 80 + "\n")
            
            return True
            
    except websockets.exceptions.InvalidURI:
        print("\n✗ Error: Invalid WebSocket URL")
        print(f"  URL: {websocket_url}")
        return False
        
    except websockets.exceptions.WebSocketException as e:
        print(f"\n✗ WebSocket Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Check if Fargate tasks are running:")
        print("     aws ecs list-tasks --cluster <cluster> --service-name <service>")
        print("  2. Check task health:")
        print("     aws ecs describe-tasks --cluster <cluster> --tasks <task-id>")
        print("  3. Check CloudWatch logs:")
        print("     aws logs tail /ecs/rag-streaming-production --follow")
        return False
        
    except ConnectionRefusedError:
        print("\n✗ Connection Refused")
        print("\nThe service might not be running. Check:")
        print("  aws ecs describe-services --cluster <cluster> --services <service>")
        return False
        
    except asyncio.TimeoutError:
        print("\n✗ Connection Timeout")
        print("\nThe service might be slow to respond. Check:")
        print("  1. ALB health checks")
        print("  2. Task logs for errors")
        return False
        
    except Exception as e:
        print(f"\n✗ Unexpected Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Main test runner"""
    
    print("\n")
    
    # Try to get URL from terraform
    websocket_url = get_websocket_url()
    
    if not websocket_url:
        # Fallback to manual input
        print("\nCouldn't auto-detect URL. Please enter it manually:")
        websocket_url = input("WebSocket URL (ws://...): ").strip()
        
        if not websocket_url:
            print("✗ No URL provided. Exiting.")
            sys.exit(1)
    
    # Test queries
    test_queries = [
        "What is the deductible for PPO plan?",
        "What are the benefits of the HMO plan?",
        "How do I file a claim?"
    ]
    
    print(f"\n{'='*80}")
    print(f"Running {len(test_queries)} test queries...")
    print(f"{'='*80}\n")
    
    # Run tests
    results = []
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'#'*80}")
        print(f"# TEST {i}/{len(test_queries)}")
        print(f"{'#'*80}\n")
        
        success = await test_rag_streaming(websocket_url, query)
        results.append(success)
        
        # Wait between tests
        if i < len(test_queries):
            print("\nWaiting 2 seconds before next test...\n")
            await asyncio.sleep(2)
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"\nTotal tests: {len(results)}")
    print(f"Passed:      {sum(results)}")
    print(f"Failed:      {len(results) - sum(results)}")
    
    if all(results):
        print("\n✓ All tests passed! 🎉\n")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed. Check logs above.\n")
        sys.exit(1)

# ============================================================================
# Run the tests
# ============================================================================

if __name__ == "__main__":
    asyncio.run(main())