import asyncio
import websockets
import json


async def test():
    uri = "ws://localhost:8081/ws/chat"
    
    async with websockets.connect(uri) as websocket:
        # Updated query with better parameters
        query = {
            "query": "What medical expenses are covered under the Optima Restore policy?",
            "top_k": 5,  # More context
            "max_tokens": 512,  # More tokens
            "temperature": 0.8  # More creative/detailed
        }
        
        print(f"\n{'='*60}")
        print(f"Query: {query['query']}")
        print(f"   Parameters:")
        print(f"   - top_k: {query['top_k']}")
        print(f"   - max_tokens: {query['max_tokens']}")
        print(f"   - temperature: {query['temperature']}")
        print(f"{'='*60}\n")
        
        await websocket.send(json.dumps(query))
        
        full_response = ""
        
        while True:
            response = await websocket.recv()
            data = json.loads(response)
            
            msg_type = data.get("type")
            
            if msg_type == "status":
                print(f"{data.get('message')}")
                
            elif msg_type == "token":
                token = data.get('content', '')
                print(token, end='', flush=True)
                full_response += token
                
            elif msg_type == "error":
                print(f"\nError: {data.get('message')}")
                if data.get('details'):
                    print(f"   Details: {data.get('details')}")
                break
                
            elif msg_type == "done":
                print(f"\n\n{data.get('message')}")
                print(f"\n{'='*60}")
                print(f"Response Stats:")
                print(f"   Length: {len(full_response)} characters")
                print(f"   Words: {len(full_response.split())} words")
                print(f"   Tokens: ~{len(full_response.split())}")
                print(f"{'='*60}")
                break


asyncio.run(test())