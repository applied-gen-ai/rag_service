import asyncio
import websockets
import json

async def test_rag():
    # Get WebSocket URL from terraform output
    url = "ws://rag-streaming-production-alb-1843797467.us-east-1.elb.amazonaws.com/ws/chat"  # Replace with actual URL
    
    async with websockets.connect(url) as websocket:
        print("Connected! Sending query...")
        
        query = {
            "query": "What is the deductible for PPO plan?",
            "stream": True
        }
        await websocket.send(json.dumps(query))
        
        print("\nResponse:")
        async for message in websocket:
            data = json.loads(message)
            if data.get("type") == "token":
                print(data["content"], end="", flush=True)
            elif data.get("type") == "done":
                print("\n\nDone!")
                break

asyncio.run(test_rag())