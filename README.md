# Hit-or-Miss: Semantic Caching for LLMs

## Problem Statement

LLM API calls are expensive and slow. In many production systems, users frequently ask semantically similar questions — yet each request triggers a fresh API call at full cost and latency.

- **Redundant API spend** — Teams pay for the same answer multiple times when users rephrase the same question ("reverse a linked list" vs "flip a linked list in Python")
- **Unnecessary latency** — LLM responses take 1-3 seconds; a cache lookup takes 10-25ms (60-160x faster)
- **No built-in semantic deduplication** — Exact-match caches miss rephrased queries entirely; semantic caching uses vector similarity to catch them
- **Model size vs accuracy trade-off is unclear** — Larger embedding models should produce better matches, but by how much? And is the extra compute worth it?
- **Vector store choice matters** — ChromaDB and Redis both support vector search, but their operational trade-offs (latency, TTL, scalability) are poorly documented for this use case
- **Hit-or-Miss quantifies all of this** — This POC benchmarks 3 embedding models × 2 vector stores × 4 similarity thresholds across 16,000 test queries to answer these questions with data

## Architecture

```
                                 Hit-or-Miss
 ┌──────────────────────────────────────────────────────────────────┐
 │                                                                  │
 │   User Prompt                                                    │
 │       │                                                          │
 │       ▼                                                          │
 │   ┌──────────────────────────────────────────────────────────┐   │
 │   │                   FastAPI Server                         │   │
 │   │   /v1/messages (Anthropic-compatible proxy endpoint)     │   │
 │   │   /playground (interactive UI)                           │   │
 │   │   /cache (inspector) · /report (benchmark viewer)        │   │
 │   └──────────┬───────────────────────────────────────────────┘   │
 │              │                                                   │
 │              ▼                                                   │
 │   ┌──────────────────┐    ┌────────────────────────────────┐    │
 │   │ Cache Middleware  │    │     Embedding Models           │    │
 │   │                  │◄───│                                │    │
 │   │ embed → search   │    │  Small:  MiniLM   (22M, 384d) │    │
 │   │ → hit/miss       │    │  Medium: MPNet    (109M, 768d) │    │
 │   │ → forward/return │    │  Large:  BGE-Large(335M,1024d) │    │
 │   └───────┬──────────┘    └────────────────────────────────┘    │
 │           │                                                      │
 │     ┌─────┴─────┐                                                │
 │     │           │                                                │
 │    HIT        MISS                                               │
 │     │           │                                                │
 │     │           ▼                                                │
 │     │    ┌─────────────┐     ┌───────────────┐                  │
 │     │    │ Forward to  │────►│ Anthropic     │                  │
 │     │    │ LLM Proxy   │     │ Claude API    │                  │
 │     │    └──────┬──────┘     └───────────────┘                  │
 │     │           │                                                │
 │     │           ▼                                                │
 │     │    ┌─────────────┐                                        │
 │     │    │ Store in    │  (prompt + embedding + response)       │
 │     │    │ Vector DB   │                                        │
 │     │    └──────┬──────┘                                        │
 │     │           │                                                │
 │     ▼           ▼                                                │
 │   ┌──────────────────────────────────────────────────────────┐   │
 │   │              Vector Store (one collection per model)     │   │
 │   │                                                          │   │
 │   │   ChromaDB (embedded, disk-backed)                       │   │
 │   │     semantic_cache_all-MiniLM-L6-v2        (384-dim)     │   │
 │   │     semantic_cache_all-mpnet-base-v2       (768-dim)     │   │
 │   │     semantic_cache_BAAI_bge-large-en-v1.5  (1024-dim)    │   │
 │   │                                                          │   │
 │   │   Redis Stack (server, in-memory)                        │   │
 │   │     semcache_BAAI_bge_large_en_v1_5        (1024-dim)    │   │
 │   └──────────────────────────────────────────────────────────┘   │
 │                                                                  │
 └──────────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Web Framework | FastAPI + Uvicorn |
| Vector Store | ChromaDB (embedded) and Redis Stack (via RedisVL) |
| Embedding Models | sentence-transformers (MiniLM, MPNet, BGE-Large) |
| LLM | Anthropic Claude API |
| HTTP Client | httpx (async) |
| UI | Jinja2 + Pico CSS + vanilla JS |

### How It Works

1. A prompt arrives at the `/v1/messages` endpoint (Anthropic-compatible)
2. The active embedding model converts it to a vector (10-25ms)
3. The vector store searches for the nearest cached prompt (cosine similarity)
4. **Cache HIT** (similarity >= threshold): return the cached response instantly
5. **Cache MISS**: forward to Claude API, store the prompt+response in the vector DB for future hits
6. The cache grows organically — every miss enriches it for future queries

Each embedding model has its own isolated collection. Embeddings from different models are never mixed.

## Benchmarking

We benchmarked **3 embedding models × 2 vector stores × 4 similarity thresholds = 16 combinations**, each tested against **1,000 queries** (100 prompt groups × 10 variants) across 10 programming domains — totalling **16,000 queries**.

### Executive Summary

| Combo | Best Threshold | F1 | Paraphrase Hit Rate | False Positive Rate | Search Latency |
|-------|---------------|-----|---------------------|---------------------|----------------|
| ChromaDB + MiniLM (22M) | 0.80 | 0.653 | 48.2% | 26.0% | 0.8ms |
| ChromaDB + MPNet (109M) | 0.80 | 0.707 | 56.8% | 25.8% | 1.0ms |
| **ChromaDB + BGE-Large (335M)** | **0.80** | **0.789** | **93.8%** | **68.5%** | **0.9ms** |
| **Redis + BGE-Large (335M)** | **0.80** | **0.789** | **93.8%** | **68.5%** | **3.9ms** |

**Key findings:**
- BGE-Large catches **93.8%** of paraphrased prompts vs 48.2% for MiniLM — the larger model makes a significant difference
- Accuracy is **identical** between ChromaDB and Redis (same embeddings, same cosine math)
- All cache lookups are **55-162x faster** than a typical LLM API call

Full benchmark report with charts: [`reports/benchmark_report_with_redis_benchmark.md`](reports/benchmark_report_with_redis_benchmark.md)

### Why is ChromaDB faster than Redis?

This is counter-intuitive — Redis is an in-memory database, so it should be faster. The explanation:

- **At this scale (~100 entries), ChromaDB runs in-process.** It uses hnswlib embedded directly in the Python process with zero network overhead. The vector search is a function call, not a network round-trip.
- **Redis requires a TCP round-trip.** Even on localhost, each `FT.SEARCH` command goes through TCP serialization, the Redis protocol, and deserialization. At ~100 entries, this network overhead dominates the actual search time.
- **At larger scale (100K+ entries), Redis would likely win.** Its in-memory HNSW implementation is highly optimized for concurrent access and scales horizontally via Redis Cluster. ChromaDB's embedded mode would degrade as it relies on SQLite + disk-backed storage.
- **Redis has a critical production advantage: native TTL.** Cache entries can auto-expire (e.g., after 24 hours), which ChromaDB cannot do without manual cleanup.

**Bottom line:** ChromaDB is the better choice for development and small-scale deployments. Redis is the better choice for production systems at scale.

## Cost Savings

Assumptions: Claude Sonnet pricing ($3/MTok input, $15/MTok output), average prompt of 200 tokens, average response of 500 tokens = **$0.0081 per API call**.

| Monthly Request Volume | Cache Hit Rate | Calls Saved | Monthly Savings |
|----------------------|----------------|-------------|-----------------|
| 10,000 | 40% | 4,000 | $32 |
| 10,000 | 60% | 6,000 | $49 |
| 10,000 | 80% | 8,000 | $65 |
| 100,000 | 40% | 40,000 | $324 |
| 100,000 | 60% | 60,000 | $486 |
| 100,000 | 80% | 80,000 | $648 |

These are conservative estimates based on short prompts. Real-world workloads with longer system prompts, RAG context, or larger responses would see proportionally higher savings.

## Future Improvements

### 1. User Context Awareness

The current system embeds only the raw prompt text. It does not consider:
- **Conversation history** — the same prompt in different conversations can mean different things
- **System prompts** — two identical user prompts with different system prompts should not match
- **User identity** — personalized responses (e.g., "explain like I'm a beginner" vs for an expert) should be cached separately

Incorporating these signals into the cache key (e.g., hashing the system prompt alongside the user message, or embedding the full conversation context) would significantly reduce false positives and improve cache relevance.

### 2. Reducing False Positive Rates

Our benchmark shows a 68.5% false positive rate on "close but different" prompts at the best F1 threshold. This is the primary accuracy gap. Potential mitigations:

- **Hybrid retrieval** — Combine vector similarity with keyword overlap detection. If two prompts are semantically close but differ on a key term ("singly linked list" vs "circular linked list"), flag the match as suspicious and skip the cache.
- **Two-stage verification** — Use a cheap, fast LLM call (e.g., Haiku) as a second check: "Are these two prompts asking for the same thing?" Only return the cached response if confirmed. This adds ~200ms but eliminates most false positives.
- **Adaptive thresholds** — Instead of a single global threshold, learn per-domain thresholds. Code generation prompts about data structures may need a higher threshold than general knowledge questions.

### 3. Other Improvements

- **Cache warm-up analysis** — Measure how hit rate improves as the cache grows from 0 to N entries, to quantify the "cold start" period
- **Concurrency load testing** — Benchmark under parallel request load (50-100 concurrent queries) to measure p95/p99 latencies and identify bottlenecks
- **TTL-based expiration** — Implement automatic cache invalidation so stale responses don't persist indefinitely (Redis supports this natively; ChromaDB would need a background sweep job)
- **Cache analytics dashboard** — A real-time UI showing hit rate trends, latency distributions, cache growth, and cost savings over time
- **Multi-model ensemble** — Use a fast small model for initial screening and fall back to the large model only for borderline similarity scores, balancing speed and accuracy

## Running the Project

```bash
# Clone and install
git clone <repo-url>
cd hit-or-miss
uv venv && source .venv/bin/activate
uv pip install -e .

# Set up environment
cp .env.example .env  # Add your ANTHROPIC_API_KEY

# Start the server
uvicorn src.main:app --reload --port 8888

# Open in browser
# Playground: http://localhost:8888/playground
# Cache Inspector: http://localhost:8888/cache
# Benchmark Report: http://localhost:8888/report

# Run benchmarks (optional — requires Redis Stack for full run)
python benchmarks/run_benchmark.py --quick                    # Quick: 1 model, 1 threshold
python benchmarks/run_benchmark.py                            # Full: 3 models + Redis, 4 thresholds
python benchmarks/generate_report.py --suffix <your_suffix>   # Generate markdown report
python benchmarks/generate_charts.py --suffix <your_suffix>   # Generate charts
```
