"""
Performance benchmarking script for AI Auditor.
"""
import asyncio
import time
from statistics import mean, median, stdev

import httpx


async def benchmark_ingest(client: httpx.AsyncClient, file_path: str, iterations: int = 10):
    """Benchmark document ingestion."""
    times = []

    print(f"\\n📊 Benchmarking Ingest ({iterations} iterations)...")

    for i in range(iterations):
        start = time.time()

        with open(file_path, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            response = await client.post("/ingest", files=files)

        elapsed = time.time() - start
        times.append(elapsed)

        if response.status_code != 200:
            print(f"❌ Request {i + 1} failed: {response.status_code}")
        else:
            print(f"✅ Request {i + 1}: {elapsed:.3f}s")

    print(f"\\nIngest Results:")
    print(f"  Mean: {mean(times):.3f}s")
    print(f"  Median: {median(times):.3f}s")
    print(f"  Std Dev: {stdev(times):.3f}s")
    print(f"  Min: {min(times):.3f}s")
    print(f"  Max: {max(times):.3f}s")


async def benchmark_query(client: httpx.AsyncClient, query: str, iterations: int = 100):
    """Benchmark query processing."""
    times = []

    print(f"\\n📊 Benchmarking Query ({iterations} iterations)...")

    for i in range(iterations):
        start = time.time()

        response = await client.post("/query", json={"query": query})

        elapsed = time.time() - start
        times.append(elapsed)

        if response.status_code != 200:
            print(f"❌ Request {i + 1} failed: {response.status_code}")
        elif (i + 1) % 10 == 0:
            print(f"✅ Completed {i + 1}/{iterations} requests")

    print(f"\\nQuery Results:")
    print(f"  Mean: {mean(times):.3f}s")
    print(f"  Median: {median(times):.3f}s")
    print(f"  Std Dev: {stdev(times):.3f}s")
    print(f"  Min: {min(times):.3f}s")
    print(f"  Max: {max(times):.3f}s")
    print(f"  Throughput: {iterations / sum(times):.2f} req/s")


async def main():
    base_url = "http://localhost:8000"
    api_key = "your-api-key"

    headers = {"X-API-Key": api_key} if api_key else {}

    async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=60.0) as client:
        # Health check
        response = await client.get("/health")
        if response.status_code != 200:
            print("❌ Service not healthy")
            return

        print("✅ Service is healthy")

        # Benchmark queries
        await benchmark_query(client, "What is the revenue?", iterations=100)

        # Note: Uncomment to benchmark ingest (requires test PDF file)
        # await benchmark_ingest(client, "test.pdf", iterations=10)


if __name__ == "__main__":
    asyncio.run(main())
