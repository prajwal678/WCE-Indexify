import asyncio
import aiohttp
import time

async def load_test_single_endpoint(url, num_requests, concurrent_requests):
    async with aiohttp.ClientSession() as session:
        tasks = []
        start_time = time.time()
        
        async def make_request():
            async with session.post(
                f"{url}/extract",
                json={
                    "url": "http://example.com",
                    "schema": {
                        "type": "object",
                        "properties": {"title": {"type": "string"}},
                        "required": ["title"]
                    }
                }
            ) as response:
                return await response.json()
        
        for _ in range(num_requests):
            tasks.append(make_request())
            if len(tasks) >= concurrent_requests:
                await asyncio.gather(*tasks)
                tasks = []
        
        if tasks:
            await asyncio.gather(*tasks)
        
        end_time = time.time()
        return end_time - start_time

async def main():
    base_url = "http://localhost:8000"
    num_requests = 1000
    concurrent_requests = 50
    
    print(f"Starting load test with {num_requests} total requests, {concurrent_requests} concurrent...")
    duration = await load_test_single_endpoint(base_url, num_requests, concurrent_requests)
    print(f"Load test completed in {duration:.2f} seconds")
    print(f"Average requests per second: {num_requests/duration:.2f}")