"""
Benchmark runner for Hit-or-Miss semantic caching.

Iterates embedding models × similarity thresholds × backends, seeds the cache
with base prompts, tests all variants, and records per-query + aggregate metrics.

Usage:
    python benchmarks/run_benchmark.py                          # full run (ChromaDB × 3 models + Redis × BGE-Large)
    python benchmarks/run_benchmark.py --quick                  # quick mode (ChromaDB × MiniLM × 1 threshold)
    python benchmarks/run_benchmark.py --backend redis --quick  # quick Redis test
"""

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from src.cache.base import CacheStoreBase
from src.cache.chroma_cache import ChromaCacheStore
from src.config import EMBEDDING_MODELS
from src.embeddings.sentence_transformer import SentenceTransformerEmbedder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Override ChromaDB persist dir for benchmarks
import src.config as config
config.CHROMA_PERSIST_DIR = "./chroma_data_benchmark"

THRESHOLDS = [0.80, 0.85, 0.90, 0.95]
QUICK_THRESHOLDS = [0.85]

# Expected hit behaviour per variant category
EXPECTED_HIT = {
    "exact_duplicate": True,
    "paraphrase": True,
    "close_but_different": False,
    "unrelated": False,
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_PROMPTS_PATH = PROJECT_ROOT / "benchmarks" / "test_prompts.json"
DEFAULT_RESULTS_PATH = PROJECT_ROOT / "reports" / "benchmark_results.json"


def load_test_prompts() -> list[dict]:
    with open(TEST_PROMPTS_PATH) as f:
        data = json.load(f)
    return data["prompt_groups"]


def make_placeholder_response(base_prompt: str) -> str:
    return f"[Placeholder response for: {base_prompt[:100]}]"


def create_cache(backend: str, model_name: str) -> CacheStoreBase:
    """Create a cache store for the given backend and model."""
    if backend == "redis":
        from src.cache.redis_cache import RedisCacheStore
        return RedisCacheStore(model_name, overwrite=True)
    return ChromaCacheStore(model_name)


def run_single_benchmark(
    model_name: str,
    threshold: float,
    prompt_groups: list[dict],
    embedder: SentenceTransformerEmbedder,
    backend: str = "chroma",
) -> dict:
    """Run benchmark for one model × threshold × backend combo."""
    logger.info("=== Benchmark: backend=%s, model=%s, threshold=%.2f ===", backend, model_name, threshold)

    cache = create_cache(backend, model_name)
    cache.clear()

    # --- Seed phase ---
    seed_start = time.perf_counter()
    base_prompts = [g["base_prompt"] for g in prompt_groups]
    base_embeddings = embedder.embed_batch(base_prompts)

    for group, embedding in zip(prompt_groups, base_embeddings):
        response_text = make_placeholder_response(group["base_prompt"])
        cache.store(
            prompt=group["base_prompt"],
            embedding=embedding.tolist(),
            response=response_text,
            metadata={"tokens_used": 0, "domain": group["domain"]},
        )
    seed_ms = (time.perf_counter() - seed_start) * 1000
    logger.info("Seeded %d base prompts in %.1fms", len(base_prompts), seed_ms)

    # --- Test phase ---
    per_query_results: list[dict] = []
    category_counts: dict[str, dict] = {
        cat: {"total": 0, "hits": 0, "correct": 0}
        for cat in EXPECTED_HIT
    }

    for group in prompt_groups:
        for category, variants in group["variants"].items():
            expected_hit = EXPECTED_HIT[category]
            for variant_prompt in variants:
                embed_start = time.perf_counter()
                embedding = embedder.embed(variant_prompt)
                embed_ms = (time.perf_counter() - embed_start) * 1000

                result = cache.search(embedding.tolist(), threshold)

                actual_hit = result.hit
                is_correct = actual_hit == expected_hit

                category_counts[category]["total"] += 1
                if actual_hit:
                    category_counts[category]["hits"] += 1
                if is_correct:
                    category_counts[category]["correct"] += 1

                per_query_results.append({
                    "group_id": group["id"],
                    "domain": group["domain"],
                    "category": category,
                    "variant_prompt": variant_prompt,
                    "expected_hit": expected_hit,
                    "actual_hit": actual_hit,
                    "is_correct": is_correct,
                    "similarity_score": round(result.similarity_score, 6),
                    "embed_latency_ms": round(embed_ms, 2),
                    "search_latency_ms": round(result.search_latency_ms, 2),
                })

    # --- Compute aggregates ---
    total_queries = len(per_query_results)
    total_hits = sum(1 for r in per_query_results if r["actual_hit"])
    total_correct = sum(1 for r in per_query_results if r["is_correct"])

    tp = sum(1 for r in per_query_results if r["actual_hit"] and r["expected_hit"])
    fp = sum(1 for r in per_query_results if r["actual_hit"] and not r["expected_hit"])
    fn = sum(1 for r in per_query_results if not r["actual_hit"] and r["expected_hit"])
    tn = sum(1 for r in per_query_results if not r["actual_hit"] and not r["expected_hit"])

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    avg_embed_ms = sum(r["embed_latency_ms"] for r in per_query_results) / total_queries
    avg_search_ms = sum(r["search_latency_ms"] for r in per_query_results) / total_queries

    aggregates = {
        "backend": backend,
        "model": model_name,
        "threshold": threshold,
        "total_queries": total_queries,
        "hit_rate": round(total_hits / total_queries, 4) if total_queries else 0,
        "accuracy": round(total_correct / total_queries, 4) if total_queries else 0,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "false_positive_rate": round(fp / (fp + tn), 4) if (fp + tn) > 0 else 0,
        "false_negative_rate": round(fn / (fn + tp), 4) if (fn + tp) > 0 else 0,
        "avg_embed_latency_ms": round(avg_embed_ms, 2),
        "avg_search_latency_ms": round(avg_search_ms, 2),
        "seed_latency_ms": round(seed_ms, 2),
        "category_breakdown": {
            cat: {
                "total": counts["total"],
                "hits": counts["hits"],
                "hit_rate": round(counts["hits"] / counts["total"], 4) if counts["total"] else 0,
                "accuracy": round(counts["correct"] / counts["total"], 4) if counts["total"] else 0,
            }
            for cat, counts in category_counts.items()
        },
    }

    logger.info(
        "Results [%s]: hit_rate=%.2f%%, precision=%.4f, recall=%.4f, F1=%.4f, FP_rate=%.4f",
        backend,
        aggregates["hit_rate"] * 100,
        precision, recall, f1,
        aggregates["false_positive_rate"],
    )

    return {
        "aggregates": aggregates,
        "per_query": per_query_results,
    }


# --- Benchmark configurations ---

# Full run: ChromaDB × 3 models + Redis × BGE-Large
FULL_COMBOS = [
    ("chroma", "all-MiniLM-L6-v2"),
    ("chroma", "all-mpnet-base-v2"),
    ("chroma", "BAAI/bge-large-en-v1.5"),
    ("redis", "BAAI/bge-large-en-v1.5"),
]

QUICK_COMBOS = [
    ("chroma", "all-MiniLM-L6-v2"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Hit-or-Miss benchmark")
    parser.add_argument("--quick", action="store_true", help="Quick mode: 1 combo, 1 threshold")
    parser.add_argument("--backend", choices=["chroma", "redis", "all"], default="all",
                        help="Run only a specific backend (default: all)")
    parser.add_argument("--output-suffix", default="",
                        help="Suffix for output filename (e.g. '_with_redis_benchmark')")
    args = parser.parse_args()

    results_path = PROJECT_ROOT / "reports" / f"benchmark_results{args.output_suffix}.json"

    if args.quick:
        if args.backend == "redis":
            combos = [("redis", "BAAI/bge-large-en-v1.5")]
        else:
            combos = QUICK_COMBOS
        thresholds = QUICK_THRESHOLDS
    else:
        combos = FULL_COMBOS
        if args.backend != "all":
            combos = [(b, m) for b, m in combos if b == args.backend]
        thresholds = THRESHOLDS

    prompt_groups = load_test_prompts()
    logger.info("Loaded %d prompt groups", len(prompt_groups))
    logger.info("Running %d combos × %d thresholds = %d benchmark runs",
                len(combos), len(thresholds), len(combos) * len(thresholds))

    all_results: list[dict] = []
    all_per_query: list[dict] = []
    loaded_embedders: dict[str, SentenceTransformerEmbedder] = {}

    for backend, model_name in combos:
        if model_name not in loaded_embedders:
            embedder = SentenceTransformerEmbedder(model_name)
            logger.info("Warming up model: %s", model_name)
            embedder.embed("warmup")
            loaded_embedders[model_name] = embedder
        embedder = loaded_embedders[model_name]

        for threshold in thresholds:
            result = run_single_benchmark(model_name, threshold, prompt_groups, embedder, backend)
            all_results.append(result["aggregates"])
            all_per_query.extend(result["per_query"])

    # Save results
    results_path.parent.mkdir(parents=True, exist_ok=True)
    backends_used = sorted(set(b for b, _ in combos))
    models_used = sorted(set(m for _, m in combos))
    output = {
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "backends": backends_used,
            "models": models_used,
            "thresholds": thresholds,
            "num_prompt_groups": len(prompt_groups),
            "quick_mode": args.quick,
            "combos": [{"backend": b, "model": m} for b, m in combos],
        },
        "aggregates": all_results,
        "per_query": all_per_query,
    }
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2)

    logger.info("Results saved to %s", results_path)


if __name__ == "__main__":
    main()
