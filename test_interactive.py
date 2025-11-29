"""
Interactive RAG client with hybrid search support
"""
import asyncio
import websockets
import json


async def interactive_chat():
    uri = "ws://localhost:8081/ws/chat"
    
    print("="*70)
    print("RAG Interactive Chat with Hybrid Search")
    print("   Features: Memory | Citations | Hybrid Search")
    print("="*70)
    print("Commands:")
    print("  • Type your question and press Enter")
    print("  • 'history' - Show conversation history")
    print("  • 'clear' - Clear conversation history")
    print("  • 'citations on/off' - Toggle source citations")
    print("  • 'hybrid on/off' - Toggle hybrid search (Dense+BM25+Rerank)")
    print("  • 'rerank on/off' - Toggle reranking")
    print("  • 'quit' or 'exit' - Disconnect")
    print("="*70)
    
    # Settings
    show_citations = True
    use_hybrid = False  # Default to dense search
    use_reranking = True
    local_conversation = []
    
    async with websockets.connect(uri) as websocket:
        print("Connected to RAG service")
        print(f"Search mode: {'Hybrid (Dense+BM25+Rerank)' if use_hybrid else 'Dense only'}\n")
        
        async def receive_messages():
            full_response = ""
            
            try:
                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    
                    msg_type = data.get("type")
                    
                    if msg_type == "status":
                        print(f"Status: {data.get('message')}")
                        
                    elif msg_type == "citation":
                        if show_citations:
                            sources = data.get("sources", [])
                            print(f"\nSources Used ({len(sources)} chunks):")
                            for source in sources:
                                score = source['score']
                                score_type = source.get('score_type', 'dense')
                                context = source['metadata'].get('context', 'N/A')
                                preview = source['text_preview']
                                print(f"   • Score: {score:.3f} ({score_type}) | Context: {context}")
                                print(f"     Preview: {preview}")
                            print()
                        
                    elif msg_type == "token":
                        token = data.get('content', '')
                        print(token, end='', flush=True)
                        full_response += token
                        
                    elif msg_type == "error":
                        print(f"\nError: {data.get('message')}")
                        if data.get('details'):
                            print(f"   {data.get('details')}")
                        print()
                        
                    elif msg_type == "done":
                        if full_response.strip():
                            local_conversation.append({
                                "role": "assistant",
                                "content": full_response.strip()
                            })
                        
                        print(f"\n{data.get('message')}")
                        turn = len(local_conversation)//2
                        print(f"Stats: Length: {len(full_response)} chars | Turn: {turn}")
                        print("\n" + "-"*70 + "\n")
                        full_response = ""
                        
            except websockets.exceptions.ConnectionClosed:
                print("\nConnection closed by server")
        
        async def send_messages():
            nonlocal show_citations, use_hybrid, use_reranking
            
            while True:
                try:
                    query_text = await asyncio.get_event_loop().run_in_executor(
                        None, 
                        lambda: input("You: ")
                    )
                    
                    query_text = query_text.strip()
                    
                    # Handle commands
                    if query_text.lower() in ['quit', 'exit', 'q']:
                        print("Disconnecting...")
                        break
                    
                    if query_text.lower() == 'history':
                        print("\nConversation History:")
                        print("="*70)
                        if not local_conversation:
                            print("(No history yet)")
                        else:
                            for i, msg in enumerate(local_conversation, 1):
                                role = "You" if msg["role"] == "user" else "Bot"
                                content = msg["content"]
                                if len(content) > 100:
                                    content = content[:100] + "..."
                                print(f"{i}. {role}: {content}")
                        print("="*70 + "\n")
                        continue
                    
                    if query_text.lower() == 'clear':
                        local_conversation.clear()
                        print("Local conversation history cleared\n")
                        continue
                    
                    if query_text.lower().startswith('citations'):
                        if 'off' in query_text.lower():
                            show_citations = False
                            print("Citations disabled\n")
                        else:
                            show_citations = True
                            print("Citations enabled\n")
                        continue
                    
                    if query_text.lower().startswith('hybrid'):
                        if 'off' in query_text.lower():
                            use_hybrid = False
                            print("Hybrid search disabled (using Dense-only)\n")
                        else:
                            use_hybrid = True
                            print("Hybrid search enabled (Dense + BM25 + Reranking)\n")
                        continue
                    
                    if query_text.lower().startswith('rerank'):
                        if 'off' in query_text.lower():
                            use_reranking = False
                            print("Reranking disabled\n")
                        else:
                            use_reranking = True
                            print("Reranking enabled\n")
                        continue
                    
                    if not query_text:
                        continue
                    
                    # Add to local conversation
                    local_conversation.append({
                        "role": "user",
                        "content": query_text
                    })
                    
                    # Send query with settings
                    query = {
                        "query": query_text,
                        "top_k": 3,
                        "max_tokens": 150,
                        "temperature": 0.1,
                        "show_citations": show_citations,
                        "use_hybrid": use_hybrid,
                        "use_reranking": use_reranking
                    }
                    
                    await websocket.send(json.dumps(query))
                    
                except EOFError:
                    print("\nDisconnecting...")
                    break
        
        try:
            await asyncio.gather(
                receive_messages(),
                send_messages()
            )
        except Exception as e:
            print(f"\nError: {str(e)}")
        finally:
            turns = len(local_conversation)//2
            print(f"Session ended ({turns} conversation turns)")


if __name__ == "__main__":
    try:
        asyncio.run(interactive_chat())
    except KeyboardInterrupt:
        print("\n\nGoodbye!")