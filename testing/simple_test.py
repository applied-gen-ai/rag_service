"""
Simple RAG Service Test - WebSocket Streaming
Tests the Fargate-deployed RAG service with streaming response from EKS LLM
"""

import asyncio
import websockets
import json
import sys

# ============================================================================
# Configuration
# ============================================================================

# Get this from: terraform output websocket_url
# OR replace with your actual ALB DNS name
WEBSOCKET_URL = "ws://rag-streaming-production-alb-1843797467.us-east-1.elb.amazonaws.com/ws/chat"

# Example: "ws://rag-streaming-production-alb-123456789.us-east-1.elb.amazonaws.com/ws/chat"

# ============================================================================
# Main Test Function
# ============================================================================

async def test_rag_streaming():
    """Send a query and receive streaming response"""
    
    print("=" * 70)
    print("RAG SERVICE - STREAMING TEST")
    print("=" * 70)
    print(f"\nConnecting to: {WEBSOCKET_URL}\n")
    
    try:
        # Connect to WebSocket
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            print("✓ Connected successfully!\n")
            
            # Prepare query
            query = {
                "query": "What is the deductible for PPO plan?",
                "stream": True
            }
            
            print(f"Sending query: {query['query']}\n")
            print("-" * 70)
            print("STREAMING RESPONSE:")
            print("-" * 70)
            
            # Send query
            await websocket.send(json.dumps(query))
            
            # Receive streaming response
            full_response = ""
            
            async for message in websocket:
                data = json.loads(message)
                
                if data.get("type") == "token":
                    # Print token without newline (streaming effect)
                    token = data["content"]
                    print(token, end="", flush=True)
                    full_response += token
                    
                elif data.get("type") == "context":
                    # Context retrieved from Qdrant
                    print(f"\n\n[Context Retrieved: {len(data.get('chunks', []))} chunks]")
                    
                elif data.get("type") == "done":
                    # Streaming complete
                    print("\n")
                    print("-" * 70)
                    print("✓ Stream complete!")
                    
                    # Show metadata
                    if "metadata" in data:
                        meta = data["metadata"]
                        print(f"\nMetadata:")
                        print(f"  - Total tokens: {meta.get('total_tokens', 'N/A')}")
                        print(f"  - Time taken: {meta.get('time_seconds', 'N/A')}s")
                    
                    break
                    
                elif data.get("type") == "error":
                    # Error occurred
                    print(f"\n\n✗ Error: {data.get('message', 'Unknown error')}")
                    break
            
            print("\n" + "=" * 70)
            print("TEST COMPLETED SUCCESSFULLY")
            print("=" * 70)
            
    except websockets.exceptions.InvalidURI:
        print("✗ Error: Invalid WebSocket URL")
        print(f"  Current URL: {WEBSOCKET_URL}")
        print("\nPlease update WEBSOCKET_URL in the script with your ALB DNS name")
        print("Get it from: terraform output websocket_url")
        sys.exit(1)
        
    except websockets.exceptions.WebSocketException as e:
        print(f"✗ WebSocket Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Check if Fargate service is running")
        print("  2. Verify ALB DNS name is correct")
        print("  3. Ensure security groups allow traffic")
        sys.exit(1)
        
    except ConnectionRefusedError:
        print("✗ Connection Refused")
        print("\nCheck if the service is running:")
        print("  aws ecs describe-services --cluster <cluster> --services <service>")
        sys.exit(1)
        
    except Exception as e:
        print(f"✗ Unexpected Error: {e}")
        sys.exit(1)

# ============================================================================
# Run the test
# ============================================================================

if __name__ == "__main__":
    print("\n")
    asyncio.run(test_rag_streaming())