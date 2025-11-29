"""
RAG Service - Load Testing Script
Tests performance with multiple concurrent requests
Measures throughput, latency, and error rates
"""

import asyncio
import websockets
import json
import time
import statistics
from datetime import datetime
import subprocess

# ============================================================================
# Configuration
# ============================================================================

# Test configuration
NUM_CONCURRENT_REQUESTS = 5  # Number of concurrent connections
NUM_QUERIES_PER_CONNECTION = 3  # Queries per connection
DELAY_BETWEEN_QUERIES = 1  # Seconds between queries in same connection

# Sample queries for testing
TEST_QUERIES = [
    "What is the deductible for PPO plan?",
    "What are the benefits of the HMO plan?",
    "How do I file a claim?",
    "What is covered under preventive care?",
    "What is the out-of-pocket maximum?",
    "Are dental services covered?",
    "What is the copay for specialist visits?",
    "Is emergency care covered?",
]

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
# Statistics Tracker
# ============================================================================

class PerformanceStats:
    """Track performance statistics"""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times = []
        self.ttft_times = []  # Time to first token
        self.token_counts = []
        self.tokens_per_second = []
        self.errors = []
    
    def add_result(self, success, response_time=None, ttft=None, token_count=None, tps=None, error=None):
        """Add a test result"""
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
            if response_time:
                self.response_times.append(response_time)
            if ttft:
                self.ttft_times.append(ttft)
            if token_count:
                self.token_counts.append(token_count)
            if tps:
                self.tokens_per_second.append(tps)
        else:
            self.failed_requests += 1
            if error:
                self.errors.append(error)
    
    def print_summary(self):
        """Print performance summary"""
        print("\n" + "="*80)
        print("LOAD TEST SUMMARY")
        print("="*80)
        
        print(f"\nRequests:")
        print(f"  Total:      {self.total_requests}")
        print(f"  Successful: {self.successful_requests} ({self.successful_requests/self.total_requests*100:.1f}%)")
        print(f"  Failed:     {self.failed_requests} ({self.failed_requests/self.total_requests*100:.1f}%)")
        
        if self.response_times:
            print(f"\nResponse Times (seconds):")
            print(f"  Min:    {min(self.response_times):.2f}")
            print(f"  Max:    {max(self.response_times):.2f}")
            print(f"  Mean:   {statistics.mean(self.response_times):.2f}")
            print(f"  Median: {statistics.median(self.response_times):.2f}")
            if len(self.response_times) > 1:
                print(f"  StdDev: {statistics.stdev(self.response_times):.2f}")
        
        if self.ttft_times:
            print(f"\nTime to First Token (seconds):")
            print(f"  Min:    {min(self.ttft_times):.2f}")
            print(f"  Max:    {max(self.ttft_times):.2f}")
            print(f"  Mean:   {statistics.mean(self.ttft_times):.2f}")
            print(f"  Median: {statistics.median(self.ttft_times):.2f}")
        
        if self.token_counts:
            print(f"\nToken Counts:")
            print(f"  Total:  {sum(self.token_counts)}")
            print(f"  Mean:   {statistics.mean(self.token_counts):.1f}")
        
        if self.tokens_per_second:
            print(f"\nThroughput (tokens/sec):")
            print(f"  Min:    {min(self.tokens_per_second):.2f}")
            print(f"  Max:    {max(self.tokens_per_second):.2f}")
            print(f"  Mean:   {statistics.mean(self.tokens_per_second):.2f}")
        
        if self.errors:
            print(f"\nErrors:")
            for i, error in enumerate(self.errors[:5], 1):  # Show first 5
                print(f"  {i}. {error}")
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more")
        
        print("\n" + "="*80 + "\n")

# ============================================================================
# Single Request Test
# ============================================================================

async def send_single_query(websocket_url, query_text, connection_id, query_id):
    """Send a single query and measure performance"""
    
    print(f"  [{connection_id}:{query_id}] Sending: {query_text[:50]}...")
    
    start_time = time.time()
    first_token_time = None
    token_count = 0
    
    try:
        async with websockets.connect(websocket_url, ping_interval=20) as websocket:
            # Send query
            query = {
                "query": query_text,
                "stream": True
            }
            await websocket.send(json.dumps(query))
            
            # Receive response
            async for message in websocket:
                data = json.loads(message)
                
                if data.get("type") == "token":
                    if first_token_time is None:
                        first_token_time = time.time()
                    token_count += 1
                    
                elif data.get("type") == "done":
                    end_time = time.time()
                    total_time = end_time - start_time
                    ttft = (first_token_time - start_time) if first_token_time else None
                    
                    # Calculate tokens per second
                    if first_token_time and token_count > 0:
                        streaming_time = end_time - first_token_time
                        tps = token_count / streaming_time if streaming_time > 0 else 0
                    else:
                        tps = 0
                    
                    print(f"  [{connection_id}:{query_id}] ✓ Complete - {total_time:.2f}s, {token_count} tokens, {tps:.1f} tok/s")
                    
                    return True, total_time, ttft, token_count, tps, None
                    
                elif data.get("type") == "error":
                    error_msg = data.get("message", "Unknown error")
                    print(f"  [{connection_id}:{query_id}] ✗ Error: {error_msg}")
                    return False, None, None, None, None, error_msg
            
            return False, None, None, None, None, "No response received"
            
    except Exception as e:
        print(f"  [{connection_id}:{query_id}] ✗ Exception: {e}")
        return False, None, None, None, None, str(e)

# ============================================================================
# Connection Worker
# ============================================================================

async def connection_worker(websocket_url, connection_id, num_queries, stats):
    """Worker that sends multiple queries on same connection"""
    
    print(f"\n[Connection {connection_id}] Starting...")
    
    for query_id in range(1, num_queries + 1):
        # Pick a random query
        import random
        query_text = random.choice(TEST_QUERIES)
        
        # Send query
        success, response_time, ttft, token_count, tps, error = await send_single_query(
            websocket_url, query_text, connection_id, query_id
        )
        
        # Record stats
        stats.add_result(success, response_time, ttft, token_count, tps, error)
        
        # Delay between queries (except last one)
        if query_id < num_queries:
            await asyncio.sleep(DELAY_BETWEEN_QUERIES)
    
    print(f"[Connection {connection_id}] Complete")

# ============================================================================
# Main Load Test
# ============================================================================

async def run_load_test(websocket_url):
    """Run load test with concurrent connections"""
    
    print("="*80)
    print("RAG SERVICE - LOAD TEST")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Endpoint:             {websocket_url}")
    print(f"  Concurrent Requests:  {NUM_CONCURRENT_REQUESTS}")
    print(f"  Queries per Request:  {NUM_QUERIES_PER_CONNECTION}")
    print(f"  Total Queries:        {NUM_CONCURRENT_REQUESTS * NUM_QUERIES_PER_CONNECTION}")
    print(f"  Delay Between:        {DELAY_BETWEEN_QUERIES}s")
    print("\n" + "="*80)
    
    # Initialize stats
    stats = PerformanceStats()
    
    # Start timer
    test_start = time.time()
    
    # Create concurrent workers
    tasks = []
    for i in range(1, NUM_CONCURRENT_REQUESTS + 1):
        task = connection_worker(websocket_url, i, NUM_QUERIES_PER_CONNECTION, stats)
        tasks.append(task)
    
    # Run all workers concurrently
    await asyncio.gather(*tasks)
    
    # End timer
    test_end = time.time()
    total_test_time = test_end - test_start
    
    # Print results
    print("\n" + "="*80)
    print(f"Load test completed in {total_test_time:.2f} seconds")
    print(f"Overall throughput: {stats.total_requests / total_test_time:.2f} requests/sec")
    
    stats.print_summary()

# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Main function"""
    
    print("\n")
    
    # Get URL
    websocket_url = get_websocket_url()
    
    if not websocket_url:
        print("Couldn't auto-detect URL. Please enter manually:")
        websocket_url = input("WebSocket URL (ws://...): ").strip()
        
        if not websocket_url:
            print("No URL provided. Exiting.")
            return
    
    # Run test
    await run_load_test(websocket_url)

# ============================================================================
# Run the load test
# ============================================================================

if __name__ == "__main__":
    asyncio.run(main())