# Hit-or-Miss — Benchmark Report
Generated: 2026-03-28T13:22:59.852827+00:00
Quick mode: Yes

## Executive Summary

- **Best model/threshold combo:** all-MiniLM-L6-v2 @ threshold 0.85
  - F1: 0.5891 | Precision: 0.7515 | Recall: 0.4844
  - Hit rate: 36.8% | False positive rate: 21.3%

- **Estimated cost savings** (assuming best combo hit rate):
  - 1,000 requests/month: ~$2.98 saved (368 cache hits)
  - 10,000 requests/month: ~$29.83 saved (3,683 cache hits)
  - 100,000 requests/month: ~$298.32 saved (36,830 cache hits)


## Model Comparison Table

| Model | Threshold | Hit Rate | Precision | Recall | F1 | FP Rate | Avg Embed (ms) | Avg Search (ms) |
|-------|-----------|----------|-----------|--------|----|---------|----------------|-----------------|
| all-MiniLM-L6-v2 | 0.85 | 36.8% | 0.7515 | 0.4844 | 0.5891 | 21.3% | 11.3 | 0.8 |

## Threshold Sensitivity Analysis

### all-MiniLM-L6-v2

| Threshold | Hit Rate | Precision | Recall | F1 | FP Rate |
|-----------|----------|-----------|--------|----|---------|
| 0.85 | 36.8% | 0.7515 | 0.4844 | 0.5891 | 21.3% |

## Results by Category

Per model at its best threshold (by F1):

### all-MiniLM-L6-v2 (threshold=0.85)

| Category | Total | Hits | Hit Rate | Accuracy | Expected |
|----------|-------|------|----------|----------|----------|
| exact_duplicate | 64 | 64 | 100.0% | 100.0% | Should be 100% |
| paraphrase | 192 | 60 | 31.2% | 31.2% | Higher is better |
| close_but_different | 128 | 28 | 21.9% | 78.1% | Lower is better |
| unrelated | 64 | 13 | 20.3% | 79.7% | Should be 0% |

## Latency Analysis

| Model | Avg Embed (ms) | Avg Search (ms) | Total Cache Lookup (ms) | vs LLM Call (~1-3s) |
|-------|----------------|-----------------|------------------------|---------------------|
| all-MiniLM-L6-v2 | 11.3 | 0.8 | 12.1 | 124x faster |

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
- 448 total queries executed
- Models: all-MiniLM-L6-v2
- Thresholds: 0.85
