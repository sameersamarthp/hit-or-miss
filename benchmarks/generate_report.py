"""
Report generator for Hit-or-Miss benchmark results.

Reads reports/benchmark_results.json and outputs reports/benchmark_report.md.

Usage:
    python benchmarks/generate_report.py
"""

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = PROJECT_ROOT / "reports" / "benchmark_results.json"
REPORT_PATH = PROJECT_ROOT / "reports" / "benchmark_report.md"

# Cost assumptions (Claude Sonnet)
COST_INPUT_PER_MTOK = 3.0   # $/MTok
COST_OUTPUT_PER_MTOK = 15.0  # $/MTok
AVG_INPUT_TOKENS = 200
AVG_OUTPUT_TOKENS = 500


def load_results() -> dict:
    with open(RESULTS_PATH) as f:
        return json.load(f)


def find_best_combo(aggregates: list[dict]) -> dict:
    """Find the model/threshold combo with the best F1 score."""
    return max(aggregates, key=lambda a: a["f1"])


def cost_per_request() -> float:
    """Estimated cost per LLM API call in dollars."""
    input_cost = (AVG_INPUT_TOKENS / 1_000_000) * COST_INPUT_PER_MTOK
    output_cost = (AVG_OUTPUT_TOKENS / 1_000_000) * COST_OUTPUT_PER_MTOK
    return input_cost + output_cost


def generate_report(data: dict) -> str:
    meta = data["metadata"]
    aggregates = data["aggregates"]
    per_query = data["per_query"]
    best = find_best_combo(aggregates)
    cpp = cost_per_request()

    lines: list[str] = []

    def w(line: str = "") -> None:
        lines.append(line)

    # --- Header ---
    w(f"# Hit-or-Miss — Benchmark Report")
    w(f"Generated: {meta['timestamp']}")
    w(f"Quick mode: {'Yes' if meta.get('quick_mode') else 'No'}")
    w()

    # --- Executive Summary ---
    w("## Executive Summary")
    w()
    w(f"- **Best model/threshold combo:** {best['model']} @ threshold {best['threshold']}")
    w(f"  - F1: {best['f1']:.4f} | Precision: {best['precision']:.4f} | Recall: {best['recall']:.4f}")
    w(f"  - Hit rate: {best['hit_rate']*100:.1f}% | False positive rate: {best['false_positive_rate']*100:.1f}%")
    w()

    w("- **Estimated cost savings** (assuming best combo hit rate):")
    for volume in [1_000, 10_000, 100_000]:
        saved_calls = int(volume * best["hit_rate"])
        savings = saved_calls * cpp
        w(f"  - {volume:,} requests/month: ~${savings:,.2f} saved ({saved_calls:,} cache hits)")
    w()

    # Compare small vs large
    small_results = [a for a in aggregates if a["model"] == "all-MiniLM-L6-v2"]
    large_results = [a for a in aggregates if a["model"] == "BAAI/bge-large-en-v1.5"]
    if small_results and large_results:
        best_small = max(small_results, key=lambda a: a["f1"])
        best_large = max(large_results, key=lambda a: a["f1"])
        f1_diff = best_large["f1"] - best_small["f1"]
        direction = "outperforms" if f1_diff > 0 else "underperforms vs"
        w(f"- **Key finding:** Large model (BGE) {direction} small model (MiniLM) by {abs(f1_diff):.4f} F1")
        latency_ratio = best_large["avg_embed_latency_ms"] / best_small["avg_embed_latency_ms"] if best_small["avg_embed_latency_ms"] > 0 else 0
        w(f"  - Embedding latency: large is {latency_ratio:.1f}x slower than small")
    w()

    # --- Model Comparison Table ---
    w("## Model Comparison Table")
    w()
    w("| Model | Threshold | Hit Rate | Precision | Recall | F1 | FP Rate | Avg Embed (ms) | Avg Search (ms) |")
    w("|-------|-----------|----------|-----------|--------|----|---------|----------------|-----------------|")
    for a in sorted(aggregates, key=lambda x: (x["model"], x["threshold"])):
        w(f"| {a['model']} | {a['threshold']} | {a['hit_rate']*100:.1f}% | {a['precision']:.4f} | {a['recall']:.4f} | {a['f1']:.4f} | {a['false_positive_rate']*100:.1f}% | {a['avg_embed_latency_ms']:.1f} | {a['avg_search_latency_ms']:.1f} |")
    w()

    # --- Threshold Sensitivity ---
    w("## Threshold Sensitivity Analysis")
    w()
    models_in_run = sorted(set(a["model"] for a in aggregates))
    for model in models_in_run:
        w(f"### {model}")
        w()
        w("| Threshold | Hit Rate | Precision | Recall | F1 | FP Rate |")
        w("|-----------|----------|-----------|--------|----|---------|")
        model_results = sorted(
            [a for a in aggregates if a["model"] == model],
            key=lambda x: x["threshold"],
        )
        for a in model_results:
            w(f"| {a['threshold']} | {a['hit_rate']*100:.1f}% | {a['precision']:.4f} | {a['recall']:.4f} | {a['f1']:.4f} | {a['false_positive_rate']*100:.1f}% |")
        w()

    # --- Results by Category ---
    w("## Results by Category")
    w()
    w(f"Per model at its best threshold (by F1):")
    w()
    for model in models_in_run:
        model_aggs = [a for a in aggregates if a["model"] == model]
        best_for_model = max(model_aggs, key=lambda a: a["f1"])
        cb = best_for_model["category_breakdown"]
        w(f"### {model} (threshold={best_for_model['threshold']})")
        w()
        w("| Category | Total | Hits | Hit Rate | Accuracy | Expected |")
        w("|----------|-------|------|----------|----------|----------|")
        expected_labels = {
            "exact_duplicate": "Should be 100%",
            "paraphrase": "Higher is better",
            "close_but_different": "Lower is better",
            "unrelated": "Should be 0%",
        }
        for cat in ["exact_duplicate", "paraphrase", "close_but_different", "unrelated"]:
            if cat in cb:
                c = cb[cat]
                w(f"| {cat} | {c['total']} | {c['hits']} | {c['hit_rate']*100:.1f}% | {c['accuracy']*100:.1f}% | {expected_labels[cat]} |")
        w()

    # --- Latency Analysis ---
    w("## Latency Analysis")
    w()
    w("| Model | Avg Embed (ms) | Avg Search (ms) | Total Cache Lookup (ms) | vs LLM Call (~1-3s) |")
    w("|-------|----------------|-----------------|------------------------|---------------------|")
    for model in models_in_run:
        model_aggs = [a for a in aggregates if a["model"] == model]
        avg_embed = sum(a["avg_embed_latency_ms"] for a in model_aggs) / len(model_aggs)
        avg_search = sum(a["avg_search_latency_ms"] for a in model_aggs) / len(model_aggs)
        total = avg_embed + avg_search
        speedup = 1500 / total if total > 0 else 0  # assume 1.5s avg LLM call
        w(f"| {model} | {avg_embed:.1f} | {avg_search:.1f} | {total:.1f} | {speedup:.0f}x faster |")
    w()

    # --- Cost Savings Projection ---
    w("## Cost Savings Projection")
    w()
    w(f"Assumptions:")
    w(f"- Claude API pricing: ${COST_INPUT_PER_MTOK}/MTok input, ${COST_OUTPUT_PER_MTOK}/MTok output (Sonnet)")
    w(f"- Average prompt: {AVG_INPUT_TOKENS} tokens, average response: {AVG_OUTPUT_TOKENS} tokens")
    w(f"- Cost per API call: ${cpp:.6f}")
    w()
    w("| Requests/Month | Hit Rate | Cached Calls | Monthly Savings |")
    w("|---------------|----------|--------------|-----------------|")
    for volume in [1_000, 10_000, 100_000]:
        for hr_label, hr in [("Low (40%)", 0.4), ("Med (60%)", 0.6), ("High (80%)", 0.8)]:
            saved = int(volume * hr)
            savings = saved * cpp
            w(f"| {volume:,} | {hr_label} | {saved:,} | ${savings:,.2f} |")
    w()

    # --- Raw Data ---
    w("## Raw Data")
    w()
    w(f"Full results: [`reports/benchmark_results.json`](benchmark_results.json)")
    w(f"- {meta['num_prompt_groups']} prompt groups tested")
    w(f"- {len(per_query)} total queries executed")
    w(f"- Models: {', '.join(meta['models'])}")
    w(f"- Thresholds: {', '.join(str(t) for t in meta['thresholds'])}")
    w()

    return "\n".join(lines)


def main() -> None:
    data = load_results()
    report = generate_report(data)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        f.write(report)

    logger.info("Report written to %s", REPORT_PATH)
    print(f"\nReport saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
