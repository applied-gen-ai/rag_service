"""
Test LLM client connection and streaming
"""
import asyncio
import os
from dotenv import load_dotenv
from llm_client import LLMClient

load_dotenv()


async def test_llm():
    print("="*60)
    print("Testing LLM Client Connection")
    print("="*60)
    
    # Get LLM endpoint
    llm_host = os.getenv("LLM_HOST")
    llm_port = int(os.getenv("LLM_PORT", "50051"))
    
    if not llm_host:
        print("LLM_HOST not set in .env")
        print("   Add: LLM_HOST=your-eks-nlb-hostname.amazonaws.com")
        return
    
    print(f"\nLLM Host: {llm_host}")
    print(f"LLM Port: {llm_port}\n")
    
    # Create client
    client = LLMClient(host=llm_host, port=llm_port)
    
    # Connect
    print("Connecting to LLM service...")
    try:
        await client.connect()
        print("Connection successful!\n")
    except Exception as e:
        print(f"Connection failed: {str(e)}")
        return
    
    # Test streaming
    print("="*60)
    print("Testing Streaming Generation")
    print("="*60)
    
    prompt = "What is machine learning?"
    print(f"\nPrompt: {prompt}")
    print("\nStreaming response:")
    print("-" * 60)
    
    try:
        full_response = ""
        
        async for token in client.stream_generate(
            prompt=prompt,
            max_tokens=100,
            temperature=0.7
        ):
            print(token, end='', flush=True)
            full_response += token
        
        print("\n" + "-" * 60)
        print(f"\nStreaming complete!")
        print(f"   Total length: {len(full_response)} characters")
        
    except Exception as e:
        print(f"\nStreaming failed: {str(e)}")
        return
    
    # Close connection
    print("\nClosing connection...")
    await client.close()
    print("Connection closed")
    
    print("\n" + "="*60)
    print("All tests passed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_llm())