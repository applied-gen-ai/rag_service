"""
Interactive RAG Chat - WebSocket Streaming
Chat with your RAG service in real-time
"""

import asyncio
import websockets
import json
import sys
import subprocess
from datetime import datetime

# ============================================================================
# Color codes for terminal
# ============================================================================

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# ============================================================================
# Get WebSocket URL
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
        return result.stdout.strip()
    except:
        return None

# ============================================================================
# Interactive Chat Function
# ============================================================================

async def interactive_chat(websocket_url):
    """
    Interactive chat with RAG service
    """
    
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}RAG SERVICE - INTERACTIVE CHAT{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    print(f"{Colors.CYAN}Connecting to: {websocket_url}{Colors.ENDC}\n")
    
    try:
        async with websockets.connect(websocket_url, ping_interval=20) as websocket:
            print(f"{Colors.GREEN}✓ Connected successfully!{Colors.ENDC}\n")
            print(f"{Colors.YELLOW}Type your questions (or 'quit' to exit){Colors.ENDC}")
            print(f"{Colors.YELLOW}Press Ctrl+C to stop{Colors.ENDC}\n")
            print("-" * 80 + "\n")
            
            conversation_count = 0
            
            while True:
                try:
                    # Get user input
                    print(f"{Colors.BOLD}{Colors.BLUE}You:{Colors.ENDC} ", end="", flush=True)
                    
                    # Run input in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    user_query = await loop.run_in_executor(None, input)
                    
                    # Check for exit
                    if user_query.strip().lower() in ['quit', 'exit', 'q']:
                        print(f"\n{Colors.YELLOW}Goodbye! 👋{Colors.ENDC}\n")
                        break
                    
                    if not user_query.strip():
                        continue
                    
                    conversation_count += 1
                    
                    # Send query
                    query = {
                        "query": user_query.strip(),
                        "stream": True,
                        "conversation_id": f"chat_{conversation_count}"
                    }
                    
                    await websocket.send(json.dumps(query))
                    
                    # Receive response
                    print(f"\n{Colors.BOLD}{Colors.GREEN}RAG Assistant:{Colors.ENDC} ", end="", flush=True)
                    
                    full_response = ""
                    
                    async for message in websocket:
                        data = json.loads(message)
                        
                        if data.get("type") == "token":
                            token = data["content"]
                            print(token, end="", flush=True)
                            full_response += token
                            
                        elif data.get("type") == "context":
                            # Silently note context retrieval
                            chunks = data.get("chunks", [])
                            
                        elif data.get("type") == "done":
                            print(f"\n\n{Colors.CYAN}[Response complete]{Colors.ENDC}\n")
                            print("-" * 80 + "\n")
                            break
                            
                        elif data.get("type") == "error":
                            print(f"\n\n{Colors.RED}Error: {data.get('message', 'Unknown error')}{Colors.ENDC}\n")
                            break
                
                except KeyboardInterrupt:
                    print(f"\n\n{Colors.YELLOW}Interrupted by user. Exiting...{Colors.ENDC}\n")
                    break
                    
                except Exception as e:
                    print(f"\n{Colors.RED}Error: {e}{Colors.ENDC}\n")
                    continue
            
            print(f"{Colors.GREEN}Session ended. Total questions asked: {conversation_count}{Colors.ENDC}\n")
            
    except websockets.exceptions.WebSocketException as e:
        print(f"{Colors.RED}✗ WebSocket Error: {e}{Colors.ENDC}")
        print(f"\n{Colors.YELLOW}Troubleshooting:{Colors.ENDC}")
        print("  1. Check if service is running")
        print("  2. Verify URL is correct")
        print("  3. Check CloudWatch logs")
        sys.exit(1)
        
    except Exception as e:
        print(f"{Colors.RED}✗ Unexpected Error: {e}{Colors.ENDC}")
        sys.exit(1)

# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Main function"""
    
    # Try auto-detect
    websocket_url = get_websocket_url()
    
    if not websocket_url:
        print(f"\n{Colors.YELLOW}Couldn't auto-detect URL from terraform.{Colors.ENDC}")
        websocket_url = input("Enter WebSocket URL (ws://...): ").strip()
        
        if not websocket_url:
            print(f"{Colors.RED}No URL provided. Exiting.{Colors.ENDC}")
            sys.exit(1)
    
    await interactive_chat(websocket_url)

# ============================================================================
# Run the interactive chat
# ============================================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Interrupted. Goodbye!{Colors.ENDC}\n")
        sys.exit(0)