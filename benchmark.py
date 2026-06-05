"""
Benchmark script for the Distributed Log Analytics Platform.
Measures real ingestion throughput and query latency.

Usage:
    python benchmark.py --host http://18.191.36.209:8000
    python benchmark.py --host http://localhost:8000
"""

import argparse
import random
import statistics
import time
import uuid

import requests

SERVICES = ["auth-service", "payment-service", "api-gateway", "user-service", "order-service"]
LEVELS = ["INFO", "INFO", "INFO", "WARN", "ERROR"]
MESSAGES = [
    "Request processed successfully",
    "Database query executed",
    "Cache miss, fetching from DB",
    "Authentication successful",
    "Payment processed",
    "User session created",
    "Request timeout, retrying",
    "Failed to connect to upstream",
]


def get_token(host, username="admin", password="admin123"):
    res = requests.post(f"{host}/auth/login", json={"username": username, "password": password})
    res.raise_for_status()
    return res.json()["access_token"]


def generate_logs(count):
    request_id = str(uuid.uuid4())
    logs = []
    for i in range(count):
        logs.append({
            "timestamp": f"2024-01-15T10:{random.randint(0,59):02d}:{random.randint(0,59):02d}Z",
            "service_name": random.choice(SERVICES),
            "log_level": random.choice(LEVELS),
            "message": random.choice(MESSAGES),
            "request_id": request_id if i % 10 == 0 else str(uuid.uuid4()),
            "latency_ms": random.randint(5, 500),
        })
    return logs, request_id


def benchmark_ingest(host, token, total_logs=5000, batch_size=100):
    print(f"\n{'='*50}")
    print(f"INGESTION BENCHMARK ({total_logs} logs, batch size {batch_size})")
    print(f"{'='*50}")

    logs, request_id = generate_logs(total_logs)
    headers = {"Authorization": f"Bearer {token}"}
    batches = [logs[i:i+batch_size] for i in range(0, total_logs, batch_size)]

    start = time.time()
    for batch in batches:
        res = requests.post(f"{host}/logs/ingest", json=batch, headers=headers)
        res.raise_for_status()
    elapsed = time.time() - start

    throughput = total_logs / elapsed
    print(f"  Total logs:     {total_logs:,}")
    print(f"  Batch size:     {batch_size}")
    print(f"  Total time:     {elapsed:.2f}s")
    print(f"  Throughput:     {throughput:,.0f} logs/sec")
    return request_id


def benchmark_query(host, token, runs=10):
    print(f"\n{'='*50}")
    print(f"QUERY LATENCY BENCHMARK ({runs} runs)")
    print(f"{'='*50}")

    headers = {"Authorization": f"Bearer {token}"}
    latencies = []

    for service in SERVICES:
        start = time.time()
        res = requests.get(
            f"{host}/logs/search",
            params={"service": service, "level": "ERROR", "hours": 1, "limit": 50},
            headers=headers,
        )
        elapsed_ms = (time.time() - start) * 1000
        if res.ok:
            data = res.json()
            source = data.get("source", "db")
            latencies.append((elapsed_ms, source))

    cache_hits = [l for l, s in latencies if s == "cache"]
    db_hits = [l for l, s in latencies if s != "cache"]

    if db_hits:
        print(f"  DB query latency (uncached):")
        print(f"    Min:  {min(db_hits):.0f}ms")
        print(f"    Max:  {max(db_hits):.0f}ms")
        print(f"    Avg:  {statistics.mean(db_hits):.0f}ms")
    if cache_hits:
        print(f"  Cache query latency:")
        print(f"    Min:  {min(cache_hits):.0f}ms")
        print(f"    Max:  {max(cache_hits):.0f}ms")
        print(f"    Avg:  {statistics.mean(cache_hits):.0f}ms")


def benchmark_trace(host, token, request_id):
    print(f"\n{'='*50}")
    print(f"TRACE LOOKUP BENCHMARK")
    print(f"{'='*50}")

    headers = {"Authorization": f"Bearer {token}"}
    latencies = []

    for _ in range(5):
        start = time.time()
        res = requests.get(f"{host}/traces/{request_id}", headers=headers)
        elapsed_ms = (time.time() - start) * 1000
        if res.ok:
            latencies.append(elapsed_ms)

    if latencies:
        print(f"  Trace lookup latency:")
        print(f"    Min:  {min(latencies):.0f}ms")
        print(f"    Max:  {max(latencies):.0f}ms")
        print(f"    Avg:  {statistics.mean(latencies):.0f}ms")


def print_resume_summary(ingest_throughput, avg_query_ms, avg_cache_ms):
    print(f"\n{'='*50}")
    print("RESUME-READY NUMBERS")
    print(f"{'='*50}")
    print(f"  Ingestion throughput:  ~{ingest_throughput:,.0f} logs/sec")
    if avg_query_ms:
        print(f"  Query latency (cold):  ~{avg_query_ms:.0f}ms")
    if avg_cache_ms:
        print(f"  Query latency (cached): ~{avg_cache_ms:.0f}ms")
    print()
    print("  Example resume bullet:")
    print(f'  "Ingested {ingest_throughput:,.0f}+ logs/sec via Kafka batching;')
    if avg_cache_ms:
        print(f'   hot-tier queries served in {avg_cache_ms:.0f}ms (cached) via Redis cache-aside."')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8000")
    parser.add_argument("--logs", type=int, default=5000)
    parser.add_argument("--batch", type=int, default=100)
    args = parser.parse_args()

    print(f"Benchmarking {args.host}")
    token = get_token(args.host)
    print("✓ Authenticated")

    request_id = benchmark_ingest(args.host, token, args.logs, args.batch)

    print("\nWaiting 3s for Kafka consumer to process logs...")
    time.sleep(3)

    benchmark_query(args.host, token)
    benchmark_trace(args.host, token, request_id)
