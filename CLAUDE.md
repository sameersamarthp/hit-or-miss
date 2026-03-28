# CLAUDE.md — Hit-or-Miss: Semantic Caching for LLMs

## Project Overview

**Hit-or-Miss** is a proof-of-concept demonstrating semantic caching for LLM request/response pairs. The system intercepts LLM API calls, checks if a semantically similar prompt has been asked before using vector similarity search, and returns the cached response instead of making an expensive API call. This serves as a cost optimization technique for teams using LLMs.

The POC compares three embedding models (small/medium/large) to analyze how model size affects semantic matching quality, latency, and overall cache effectiveness.

## Tech Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI + Uvicorn
- **Vector Store:** ChromaDB (single instance, one collection per embedding model)
- **Embedding Models (all local, via sentence-transformers):**
  - Small: `all-MiniLM-L6-v2` (22M params, 384-dim)
  - Medium: `all-mpnet-base-v2` (109M params, 768-dim)
  - Large: `nomic-ai/nomic-embed-text-v1.5` (137M params, 768-dim)
- **LLM Proxy:** Anthropic Claude API (`/v1/messages`). OpenAI support can be added later but is out of scope for now.
- **HTTP Client:** httpx (async)
- **Environment:** macOS, Apple M2, 32GB RAM. sentence-transformers will use MPS (Metal) acceleration automatically.

## Dependencies

```
sentence-transformers
chromadb
fastapi
uvicorn[standard]
httpx
numpy
jinja2           # For server-rendered HTML templates
python-dotenv    # For API keys
```

## Project Structure

```
hit-or-miss/
├── CLAUDE.md
├── pyproject.toml
├── .env                           # ANTHROPIC_API_KEY, OPENAI_API_KEY
├── src/
│   ├── __init__.py
│   ├── config.py                  # Model names, thresholds, ChromaDB settings
│   ├── main.py                    # FastAPI app entry point
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract CacheStore interface
│   │   └── chroma_cache.py        # ChromaDB implementation (collection-per-model)
│   ├── embeddings/
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract Embedder interface
│   │   └── sentence_transformer.py  # SentenceTransformerEmbedder (accepts any model name)
│   ├── proxy/
│   │   ├── __init__.py
│   │   ├── llm_proxy.py           # Forwards requests to Claude or OpenAI
│   │   └── cache_middleware.py    # Core logic: embed → search → hit/miss → respond or forward
│   └── templates/
│       ├── playground.html        # Prompt playground page
│       ├── cache_inspector.html   # View/clear cached entries
│       └── report.html            # Renders benchmark markdown report
├── benchmarks/
│   ├── test_prompts.json          # Labeled test dataset (~60-80 prompt groups)
│   ├── run_benchmark.py           # Automated benchmark runner
│   └── generate_report.py         # Reads results JSON, outputs markdown report
├── reports/                       # Auto-generated markdown reports go here
└── README.md
```

## Architecture & Core Flow

### Cache Lookup Flow (cache_middleware.py)

```
1. Incoming request hits FastAPI endpoint
2. Extract prompt text from request body (handle Anthropic message format)
3. Generate embedding using the currently selected model
4. Search the model's ChromaDB collection for nearest neighbor
5. If similarity_score >= threshold:
     → Cache HIT: return stored response, log hit with score and latency
6. Else:
     → Cache MISS: forward request to real LLM via llm_proxy
     → Store prompt embedding + LLM response in ChromaDB collection
     → Return response, log miss with latency
```

### Embedding Model Switching

- Each embedding model gets its own ChromaDB collection: `semantic_cache_{model_name}`
- Models are lazy-loaded — switching models just changes a config string, the next call loads the new model
- Collections are independent — embeddings from different models are NEVER mixed
- The playground UI has a dropdown to switch models; the benchmark runner iterates all three programmatically
- No app restart needed to switch models

### ChromaDB Collection Strategy

```
semantic_cache_all-MiniLM-L6-v2         (384-dim vectors)
semantic_cache_all-mpnet-base-v2        (768-dim vectors)
semantic_cache_nomic-embed-text-v1.5    (768-dim vectors)
```

Each collection stores:
- `id`: unique hash of the prompt text
- `embedding`: vector from the respective model
- `document`: the original prompt text
- `metadata`: { response: str, timestamp: str, hit_count: int, tokens_used: int }

## Abstract Interfaces

### Embedder (embeddings/base.py)

```python
from abc import ABC, abstractmethod
import numpy as np

class EmbedderBase(ABC):
    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        """Generate embedding vector for a text string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for a batch of texts."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass
```

### CacheStore (cache/base.py)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class CacheResult:
    hit: bool
    similarity_score: float
    cached_prompt: str | None
    cached_response: str | None
    search_latency_ms: float

class CacheStoreBase(ABC):
    @abstractmethod
    def search(self, embedding: list[float], threshold: float) -> CacheResult:
        """Search for a similar prompt. Return CacheResult."""
        pass

    @abstractmethod
    def store(self, prompt: str, embedding: list[float], response: str, metadata: dict) -> None:
        """Store a prompt-response pair with its embedding."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries in this cache."""
        pass

    @abstractmethod
    def get_all_entries(self) -> list[dict]:
        """Return all cached entries (for the inspector UI)."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Return number of entries in cache."""
        pass
```

## API Endpoints

### LLM Proxy Endpoints
- `POST /v1/messages` — Anthropic-compatible endpoint (cache-aware)

### UI Pages
- `GET /playground` — Interactive prompt testing page
- `GET /cache` — Cache inspector (view entries, clear cache)
- `GET /report` — Rendered benchmark report

### Management Endpoints
- `GET /api/stats` — Cache statistics (hit rate, entry count, avg latency)
- `POST /api/cache/clear` — Clear cache for a specific model or all models
- `GET /api/models` — List available embedding models and their status
- `POST /api/model/switch` — Switch active embedding model

## Playground UI (playground.html)

Server-rendered HTML via Jinja2. Keep it simple — no JS frameworks. Use minimal CSS (or classless CSS like pico.css) and a bit of htmx or vanilla JS for form submission without page reload.

### Elements:
- **Text area** for entering a prompt
- **Dropdown** to select embedding model (small / medium / large)
- **Slider** for similarity threshold (0.70 to 0.99, default 0.85)
- **Submit button**
- **Results panel** showing:
  - Cache HIT / MISS badge (green/red)
  - Similarity score (if hit)
  - Matched prompt text (if hit, to see what it matched against)
  - LLM response
  - Latency breakdown: embedding time, search time, LLM call time (if miss), total time
- **Recent queries log** at the bottom showing last 10 queries with hit/miss status

## Cache Inspector UI (cache_inspector.html)

- Table of all cached entries for the selected model: prompt (truncated), timestamp, hit count
- Dropdown to switch between model collections
- "Clear Cache" button per model
- Entry count per model

## Benchmark System

### Test Dataset (benchmarks/test_prompts.json)

~60-80 prompt groups in the domain of **code generation prompts that developers would use**. Structure:

```json
{
  "prompt_groups": [
    {
      "id": "linked_list_reverse",
      "domain": "data_structures",
      "base_prompt": "Write a Python function to reverse a linked list",
      "variants": {
        "exact_duplicate": [
          "Write a Python function to reverse a linked list"
        ],
        "paraphrase": [
          "Can you give me code that reverses a singly linked list in Python?",
          "Implement linked list reversal in Python"
        ],
        "close_but_different": [
          "Write a Python function to sort a linked list",
          "Write a Python function to detect a cycle in a linked list"
        ],
        "unrelated": [
          "How do I set up a Docker container for PostgreSQL?"
        ]
      }
    }
  ]
}
```

**Domains to cover:** data structures, API development (FastAPI/Flask), file I/O, database queries (SQL/ORM), async programming, testing (pytest), CLI tools, string manipulation, error handling, web scraping. Aim for 8-10 groups per domain, 6-8 domains.

### Expected Cache Behavior per Category:
- `exact_duplicate` → MUST hit (if not, something is broken)
- `paraphrase` → SHOULD hit (this is what we're benchmarking)
- `close_but_different` → SHOULD NOT hit (false positives are bad)
- `unrelated` → MUST NOT hit (if it does, threshold is too low)

### Benchmark Runner (benchmarks/run_benchmark.py)

```
For each model in [MiniLM, mpnet, nomic]:
    For each threshold in [0.80, 0.85, 0.90, 0.95]:
        1. Load the embedding model
        2. Create/clear its ChromaDB collection
        3. Seed the cache: embed and store all base_prompts (simulate real LLM responses or use placeholder text)
        4. Run every variant prompt against the cache
        5. Record per-query: hit/miss, similarity_score, expected_hit (based on category), embed_latency_ms, search_latency_ms
        6. Compute aggregates: hit_rate, false_positive_rate, false_negative_rate, precision, recall, f1, avg_latencies

Save all results to reports/benchmark_results.json
```

For seeding: call the actual LLM for base prompts OR use deterministic placeholder responses (to avoid API costs during benchmarking). Make this configurable. Default to placeholder responses.

### Report Generator (benchmarks/generate_report.py)

Reads `benchmark_results.json`, outputs `reports/benchmark_report.md`.

**Report sections:**

```markdown
# Hit-or-Miss — Benchmark Report
Generated: {timestamp}

## Executive Summary
- Best model/threshold combo for balancing hit rate and precision
- Estimated cost savings at 1K, 10K, 100K requests/month
- Key finding: does a larger model meaningfully outperform the small one?

## Model Comparison Table
| Model | Threshold | Hit Rate | Precision | Recall | F1 | False Positive % | Avg Embed Latency | Avg Search Latency |
|-------|-----------|----------|-----------|--------|----|------------------|-------------------|--------------------|

## Threshold Sensitivity Analysis
Per model: how do metrics change as threshold moves from 0.80 → 0.95

## Results by Category
Per model at its best threshold:
- Exact duplicates: X% hit rate (should be 100%)
- Paraphrases: X% hit rate (the key metric)
- Close but different: X% false positive rate (lower is better)
- Unrelated: X% false positive rate (should be 0%)

## Latency Analysis
Embedding time per model, search time, comparison to typical LLM response time (~1-3s)

## Cost Savings Projection
Based on:
- Claude API: $3/MTok input, $15/MTok output (Sonnet)
- Average prompt: ~200 tokens, average response: ~500 tokens
- At various cache hit rates, project monthly savings

## Raw Data
Link to full JSON results
```

## Build Order for Claude Code

### Session 1 — Core cache working end-to-end
1. Initialize project: pyproject.toml, .env, directory structure
2. Implement EmbedderBase + SentenceTransformerEmbedder
3. Implement CacheStoreBase + ChromaCacheStore (with collection-per-model)
4. Implement CacheMiddleware (embed → search → hit/miss logic)
5. Implement LLMProxy (forward to Anthropic Claude API)
6. Wire into FastAPI main.py with the /v1/messages proxy endpoint
7. Test with curl: send a prompt, get response (MISS), send same prompt again (HIT)

### Session 2 — Dataset + benchmark
1. Generate test_prompts.json with 60-80 prompt groups across code generation domains
2. Build run_benchmark.py: iterate models × thresholds, seed → test → record
3. Run a quick sanity check benchmark with one model
4. Build generate_report.py: JSON → markdown with all report sections
5. Generate initial report

### Session 3 — UI + polish
1. Add Jinja2 templates: playground, cache inspector, report viewer
2. Wire up UI routes in main.py
3. Add htmx or vanilla JS for async form submission on playground
4. Add /api/stats, /api/models, /api/cache/clear endpoints
5. Run full benchmark, generate final report
6. Write README.md with setup instructions, architecture overview, usage guide

## Coding Guidelines

- Use Python type hints everywhere
- Use async/await for FastAPI endpoints and httpx calls
- Embedding model loading can be synchronous (it's a one-time cost)
- Use dataclasses or Pydantic models for structured data
- Keep functions small and single-purpose
- Log all cache operations (hit/miss, score, latency) using Python's logging module
- Use `time.perf_counter()` for latency measurements
- Handle API key missing gracefully — if no API keys in .env, the proxy endpoints should return a clear error but the playground should still work with cached responses
- For nomic model, the input text needs to be prefixed with "search_query: " or "search_document: " — handle this in the embedder implementation

## Environment Variables (.env)

```
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_EMBEDDING_MODEL=all-MiniLM-L6-v2
DEFAULT_SIMILARITY_THRESHOLD=0.85
CHROMA_PERSIST_DIR=./chroma_data
```

## Running the App

```bash
# Install dependencies
pip install -e .

# Start the server
uvicorn src.main:app --reload --port 8000

# Run benchmarks
python benchmarks/run_benchmark.py

# Generate report
python benchmarks/generate_report.py
```
