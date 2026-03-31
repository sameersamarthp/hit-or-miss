# Hit-or-Miss — Benchmark Report
Generated: 2026-03-31T15:21:59.244066+00:00
Quick mode: No

## Executive Summary

- **Best combo:** Chroma + BAAI/bge-large-en-v1.5 @ threshold 0.85
  - F1: 0.7828 | Precision: 0.7243 | Recall: 0.8516
  - Hit rate: 67.2% | False positive rate: 43.2%

- **Estimated cost savings** (assuming best combo hit rate):
  - 1,000 requests/month: ~$5.44 saved (671 cache hits)
  - 10,000 requests/month: ~$54.42 saved (6,719 cache hits)
  - 100,000 requests/month: ~$544.24 saved (67,190 cache hits)

- **Model size finding:** Large model (BGE) outperforms small model (MiniLM) by 0.0604 F1
  - Embedding latency: large is 2.0x slower than small

- **Backend comparison (BGE-Large):** ChromaDB vs Redis
  - Accuracy is identical (same embeddings, same similarity math)
  - Search latency: Redis 3.5ms vs ChromaDB 0.9ms (0.3x slower)

## Full Comparison Table

| Backend | Model | Threshold | Hit Rate | Precision | Recall | F1 | FP Rate | Avg Embed (ms) | Avg Search (ms) |
|---------|-------|-----------|----------|-----------|--------|----|---------|----------------|-----------------|
| chroma | BAAI/bge-large-en-v1.5 | 0.8 | 86.6% | 0.6495 | 0.9844 | 0.7826 | 70.8% | 22.2 | 1.0 |
| chroma | BAAI/bge-large-en-v1.5 | 0.85 | 67.2% | 0.7243 | 0.8516 | 0.7828 | 43.2% | 20.6 | 0.9 |
| chroma | BAAI/bge-large-en-v1.5 | 0.9 | 38.6% | 0.7341 | 0.4961 | 0.5921 | 24.0% | 20.4 | 0.8 |
| chroma | BAAI/bge-large-en-v1.5 | 0.95 | 17.2% | 0.8961 | 0.2695 | 0.4144 | 4.2% | 20.8 | 0.8 |
| chroma | all-MiniLM-L6-v2 | 0.8 | 52.2% | 0.7564 | 0.6914 | 0.7224 | 29.7% | 10.3 | 0.9 |
| chroma | all-MiniLM-L6-v2 | 0.85 | 36.8% | 0.7515 | 0.4844 | 0.5891 | 21.3% | 9.2 | 0.9 |
| chroma | all-MiniLM-L6-v2 | 0.9 | 23.4% | 0.8000 | 0.3281 | 0.4654 | 10.9% | 8.7 | 1.0 |
| chroma | all-MiniLM-L6-v2 | 0.95 | 16.3% | 0.9315 | 0.2656 | 0.4134 | 2.6% | 9.6 | 0.9 |
| chroma | all-mpnet-base-v2 | 0.8 | 58.3% | 0.7701 | 0.7852 | 0.7776 | 31.2% | 21.8 | 0.8 |
| chroma | all-mpnet-base-v2 | 0.85 | 40.6% | 0.7912 | 0.5625 | 0.6575 | 19.8% | 15.4 | 0.8 |
| chroma | all-mpnet-base-v2 | 0.9 | 24.8% | 0.8288 | 0.3594 | 0.5014 | 9.9% | 15.7 | 0.8 |
| chroma | all-mpnet-base-v2 | 0.95 | 16.7% | 0.9467 | 0.2773 | 0.4290 | 2.1% | 16.2 | 0.9 |
| redis | BAAI/bge-large-en-v1.5 | 0.8 | 86.6% | 0.6495 | 0.9844 | 0.7826 | 70.8% | 23.4 | 3.9 |
| redis | BAAI/bge-large-en-v1.5 | 0.85 | 67.2% | 0.7243 | 0.8516 | 0.7828 | 43.2% | 21.8 | 3.5 |
| redis | BAAI/bge-large-en-v1.5 | 0.9 | 38.6% | 0.7341 | 0.4961 | 0.5921 | 24.0% | 22.4 | 4.2 |
| redis | BAAI/bge-large-en-v1.5 | 0.95 | 17.2% | 0.8961 | 0.2695 | 0.4144 | 4.2% | 22.4 | 3.7 |

## Threshold Sensitivity Analysis

### Chroma + BAAI/bge-large-en-v1.5

| Threshold | Hit Rate | Precision | Recall | F1 | FP Rate |
|-----------|----------|-----------|--------|----|---------|
| 0.8 | 86.6% | 0.6495 | 0.9844 | 0.7826 | 70.8% |
| 0.85 | 67.2% | 0.7243 | 0.8516 | 0.7828 | 43.2% |
| 0.9 | 38.6% | 0.7341 | 0.4961 | 0.5921 | 24.0% |
| 0.95 | 17.2% | 0.8961 | 0.2695 | 0.4144 | 4.2% |

### Chroma + all-MiniLM-L6-v2

| Threshold | Hit Rate | Precision | Recall | F1 | FP Rate |
|-----------|----------|-----------|--------|----|---------|
| 0.8 | 52.2% | 0.7564 | 0.6914 | 0.7224 | 29.7% |
| 0.85 | 36.8% | 0.7515 | 0.4844 | 0.5891 | 21.3% |
| 0.9 | 23.4% | 0.8000 | 0.3281 | 0.4654 | 10.9% |
| 0.95 | 16.3% | 0.9315 | 0.2656 | 0.4134 | 2.6% |

### Chroma + all-mpnet-base-v2

| Threshold | Hit Rate | Precision | Recall | F1 | FP Rate |
|-----------|----------|-----------|--------|----|---------|
| 0.8 | 58.3% | 0.7701 | 0.7852 | 0.7776 | 31.2% |
| 0.85 | 40.6% | 0.7912 | 0.5625 | 0.6575 | 19.8% |
| 0.9 | 24.8% | 0.8288 | 0.3594 | 0.5014 | 9.9% |
| 0.95 | 16.7% | 0.9467 | 0.2773 | 0.4290 | 2.1% |

### Redis + BAAI/bge-large-en-v1.5

| Threshold | Hit Rate | Precision | Recall | F1 | FP Rate |
|-----------|----------|-----------|--------|----|---------|
| 0.8 | 86.6% | 0.6495 | 0.9844 | 0.7826 | 70.8% |
| 0.85 | 67.2% | 0.7243 | 0.8516 | 0.7828 | 43.2% |
| 0.9 | 38.6% | 0.7341 | 0.4961 | 0.5921 | 24.0% |
| 0.95 | 17.2% | 0.8961 | 0.2695 | 0.4144 | 4.2% |

## Results by Category

Per combo at its best threshold (by F1):

### Chroma + BAAI/bge-large-en-v1.5 (threshold=0.85)

| Category | Total | Hits | Hit Rate | Accuracy | Expected |
|----------|-------|------|----------|----------|----------|
| exact_duplicate | 64 | 64 | 100.0% | 100.0% | Should be 100% |
| paraphrase | 192 | 154 | 80.2% | 80.2% | Higher is better |
| close_but_different | 128 | 64 | 50.0% | 50.0% | Lower is better |
| unrelated | 64 | 19 | 29.7% | 70.3% | Should be 0% |

### Chroma + all-MiniLM-L6-v2 (threshold=0.8)

| Category | Total | Hits | Hit Rate | Accuracy | Expected |
|----------|-------|------|----------|----------|----------|
| exact_duplicate | 64 | 64 | 100.0% | 100.0% | Should be 100% |
| paraphrase | 192 | 113 | 58.9% | 58.9% | Higher is better |
| close_but_different | 128 | 40 | 31.2% | 68.8% | Lower is better |
| unrelated | 64 | 17 | 26.6% | 73.4% | Should be 0% |

### Chroma + all-mpnet-base-v2 (threshold=0.8)

| Category | Total | Hits | Hit Rate | Accuracy | Expected |
|----------|-------|------|----------|----------|----------|
| exact_duplicate | 64 | 64 | 100.0% | 100.0% | Should be 100% |
| paraphrase | 192 | 137 | 71.4% | 71.4% | Higher is better |
| close_but_different | 128 | 44 | 34.4% | 65.6% | Lower is better |
| unrelated | 64 | 16 | 25.0% | 75.0% | Should be 0% |

### Redis + BAAI/bge-large-en-v1.5 (threshold=0.85)

| Category | Total | Hits | Hit Rate | Accuracy | Expected |
|----------|-------|------|----------|----------|----------|
| exact_duplicate | 64 | 64 | 100.0% | 100.0% | Should be 100% |
| paraphrase | 192 | 154 | 80.2% | 80.2% | Higher is better |
| close_but_different | 128 | 64 | 50.0% | 50.0% | Lower is better |
| unrelated | 64 | 19 | 29.7% | 70.3% | Should be 0% |

## Latency Analysis

| Backend | Model | Avg Embed (ms) | Avg Search (ms) | Total Cache Lookup (ms) | vs LLM Call (~1-3s) |
|---------|-------|----------------|-----------------|------------------------|---------------------|
| chroma | BAAI/bge-large-en-v1.5 | 21.0 | 0.9 | 21.9 | 69x faster |
| chroma | all-MiniLM-L6-v2 | 9.4 | 0.9 | 10.4 | 144x faster |
| chroma | all-mpnet-base-v2 | 17.3 | 0.8 | 18.1 | 83x faster |
| redis | BAAI/bge-large-en-v1.5 | 22.5 | 3.8 | 26.3 | 57x faster |

## Cost Savings Projection

Assumptions:
- Claude API pricing: $3.0/MTok input, $15.0/MTok output (Sonnet)
- Average prompt: 200 tokens, average response: 500 tokens
- Cost per API call: $0.008100

| Requests/Month | Hit Rate | Cached Calls | Monthly Savings |
|---------------|----------|--------------|-----------------|
| 1,000 | Low (40%) | 400 | $3.24 |
| 1,000 | Med (60%) | 600 | $4.86 |
| 1,000 | High (80%) | 800 | $6.48 |
| 10,000 | Low (40%) | 4,000 | $32.40 |
| 10,000 | Med (60%) | 6,000 | $48.60 |
| 10,000 | High (80%) | 8,000 | $64.80 |
| 100,000 | Low (40%) | 40,000 | $324.00 |
| 100,000 | Med (60%) | 60,000 | $486.00 |
| 100,000 | High (80%) | 80,000 | $648.00 |

## Raw Data

Full results: [`reports/benchmark_results.json`](benchmark_results.json)
- 64 prompt groups tested
- 7168 total queries executed
- Backends: chroma, redis
- Models: BAAI/bge-large-en-v1.5, all-MiniLM-L6-v2, all-mpnet-base-v2
- Thresholds: 0.8, 0.85, 0.9, 0.95
