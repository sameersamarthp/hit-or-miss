"""
Generate research paper styled charts from benchmark results.

Usage:
    python benchmarks/generate_charts.py --suffix _with_redis_benchmark
"""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Research paper style
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "legend.fontsize": 9,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "--",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

CATEGORY_LABELS = {
    "exact_duplicate": "Exact Duplicate",
    "paraphrase": "Paraphrase",
    "close_but_different": "Close but Different",
    "unrelated": "Unrelated",
}

CATEGORY_COLORS = {
    "exact_duplicate": "#2ecc40",
    "paraphrase": "#0074D9",
    "close_but_different": "#FF851B",
    "unrelated": "#e74c3c",
}

CATEGORY_MARKERS = {
    "exact_duplicate": "o",
    "paraphrase": "s",
    "close_but_different": "^",
    "unrelated": "D",
}


def load_results(suffix: str) -> dict:
    path = PROJECT_ROOT / "reports" / f"benchmark_results{suffix}.json"
    with open(path) as f:
        return json.load(f)


def combo_label(backend: str, model: str) -> str:
    short_model = model.split("/")[-1] if "/" in model else model
    return f"{backend.capitalize()} + {short_model}"


def fig1_category_hit_rates_per_combo(aggregates: list[dict], output_dir: Path) -> Path:
    """Figure 1: Category hit rates across thresholds, one subplot per combo."""
    combos = []
    seen = set()
    for a in aggregates:
        key = (a.get("backend", "chroma"), a["model"])
        if key not in seen:
            seen.add(key)
            combos.append(key)

    fig, axes = plt.subplots(2, 2, figsize=(12, 9), sharey=True)
    axes = axes.flatten()

    for idx, (backend, model) in enumerate(combos):
        ax = axes[idx]
        combo_aggs = sorted(
            [a for a in aggregates if a.get("backend", "chroma") == backend and a["model"] == model],
            key=lambda x: x["threshold"],
        )
        thresholds = [a["threshold"] for a in combo_aggs]

        for cat in ["exact_duplicate", "paraphrase", "close_but_different", "unrelated"]:
            hit_rates = [a["category_breakdown"][cat]["hit_rate"] * 100 for a in combo_aggs]
            ax.plot(thresholds, hit_rates,
                    marker=CATEGORY_MARKERS[cat],
                    color=CATEGORY_COLORS[cat],
                    label=CATEGORY_LABELS[cat],
                    linewidth=2, markersize=7)

        ax.set_title(combo_label(backend, model), fontweight="bold")
        ax.set_xlabel("Similarity Threshold")
        ax.set_ylabel("Hit Rate (%)")
        ax.set_ylim(-5, 105)
        ax.set_xticks(thresholds)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))

    axes[0].legend(loc="upper right", framealpha=0.9)
    fig.suptitle("Figure 1: Category Hit Rates Across Similarity Thresholds", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()

    path = output_dir / "fig1_category_hit_rates.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def fig2_precision_recall_f1(aggregates: list[dict], output_dir: Path) -> Path:
    """Figure 2: Precision, Recall, F1 across thresholds per combo."""
    combos = []
    seen = set()
    for a in aggregates:
        key = (a.get("backend", "chroma"), a["model"])
        if key not in seen:
            seen.add(key)
            combos.append(key)

    fig, axes = plt.subplots(2, 2, figsize=(12, 9), sharey=True)
    axes = axes.flatten()

    metrics = [
        ("precision", "Precision", "#0074D9", "s"),
        ("recall", "Recall", "#2ecc40", "^"),
        ("f1", "F1 Score", "#e74c3c", "o"),
    ]

    for idx, (backend, model) in enumerate(combos):
        ax = axes[idx]
        combo_aggs = sorted(
            [a for a in aggregates if a.get("backend", "chroma") == backend and a["model"] == model],
            key=lambda x: x["threshold"],
        )
        thresholds = [a["threshold"] for a in combo_aggs]

        for key, label, color, marker in metrics:
            values = [a[key] for a in combo_aggs]
            ax.plot(thresholds, values, marker=marker, color=color, label=label,
                    linewidth=2, markersize=7)

        ax.set_title(combo_label(backend, model), fontweight="bold")
        ax.set_xlabel("Similarity Threshold")
        ax.set_ylabel("Score")
        ax.set_ylim(-0.05, 1.05)
        ax.set_xticks(thresholds)

    axes[0].legend(loc="lower left", framealpha=0.9)
    fig.suptitle("Figure 2: Precision, Recall & F1 Across Similarity Thresholds", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()

    path = output_dir / "fig2_precision_recall_f1.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def fig3_backend_comparison(aggregates: list[dict], output_dir: Path) -> Path:
    """Figure 3: ChromaDB vs Redis side-by-side (BGE-Large only)."""
    chroma = sorted(
        [a for a in aggregates if a["model"] == "BAAI/bge-large-en-v1.5" and a.get("backend", "chroma") == "chroma"],
        key=lambda x: x["threshold"],
    )
    redis = sorted(
        [a for a in aggregates if a["model"] == "BAAI/bge-large-en-v1.5" and a.get("backend") == "redis"],
        key=lambda x: x["threshold"],
    )

    if not chroma or not redis:
        return None

    thresholds = [a["threshold"] for a in chroma]
    x = np.arange(len(thresholds))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Left: F1 comparison
    bars1 = ax1.bar(x - width/2, [a["f1"] for a in chroma], width, label="ChromaDB", color="#0074D9", alpha=0.85)
    bars2 = ax1.bar(x + width/2, [a["f1"] for a in redis], width, label="Redis", color="#e74c3c", alpha=0.85)
    ax1.set_xlabel("Similarity Threshold")
    ax1.set_ylabel("F1 Score")
    ax1.set_title("F1 Score: ChromaDB vs Redis", fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels([str(t) for t in thresholds])
    ax1.legend()
    ax1.set_ylim(0, 1.0)
    ax1.bar_label(bars1, fmt="%.3f", fontsize=8, padding=2)
    ax1.bar_label(bars2, fmt="%.3f", fontsize=8, padding=2)

    # Right: Search latency comparison
    bars3 = ax2.bar(x - width/2, [a["avg_search_latency_ms"] for a in chroma], width, label="ChromaDB", color="#0074D9", alpha=0.85)
    bars4 = ax2.bar(x + width/2, [a["avg_search_latency_ms"] for a in redis], width, label="Redis", color="#e74c3c", alpha=0.85)
    ax2.set_xlabel("Similarity Threshold")
    ax2.set_ylabel("Avg Search Latency (ms)")
    ax2.set_title("Search Latency: ChromaDB vs Redis", fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels([str(t) for t in thresholds])
    ax2.legend()
    ax2.bar_label(bars3, fmt="%.1f", fontsize=8, padding=2)
    ax2.bar_label(bars4, fmt="%.1f", fontsize=8, padding=2)

    fig.suptitle("Figure 3: Backend Comparison — BGE-Large", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()

    path = output_dir / "fig3_backend_comparison.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def fig4_model_comparison_at_best_threshold(aggregates: list[dict], output_dir: Path) -> Path:
    """Figure 4: All models at their best F1 threshold — grouped bar chart of category hit rates."""
    combos = []
    seen = set()
    for a in aggregates:
        key = (a.get("backend", "chroma"), a["model"])
        if key not in seen:
            seen.add(key)
            combos.append(key)

    best_per_combo = []
    for backend, model in combos:
        combo_aggs = [a for a in aggregates if a.get("backend", "chroma") == backend and a["model"] == model]
        best = max(combo_aggs, key=lambda a: a["f1"])
        best_per_combo.append(best)

    categories = ["paraphrase", "close_but_different", "unrelated"]
    x = np.arange(len(categories))
    width = 0.18
    offsets = np.linspace(-width * (len(best_per_combo) - 1) / 2, width * (len(best_per_combo) - 1) / 2, len(best_per_combo))

    combo_colors = ["#0074D9", "#2ecc40", "#FF851B", "#e74c3c"]

    fig, ax = plt.subplots(figsize=(10, 6))

    for i, a in enumerate(best_per_combo):
        backend = a.get("backend", "chroma")
        label = f"{combo_label(backend, a['model'])} (t={a['threshold']})"
        values = [a["category_breakdown"][cat]["hit_rate"] * 100 for cat in categories]
        bars = ax.bar(x + offsets[i], values, width, label=label, color=combo_colors[i % len(combo_colors)], alpha=0.85)
        ax.bar_label(bars, fmt="%.0f%%", fontsize=8, padding=2)

    ax.set_xlabel("Category")
    ax.set_ylabel("Hit Rate (%)")
    ax.set_title("Figure 4: Category Hit Rates at Best F1 Threshold Per Model", fontweight="bold", fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels([CATEGORY_LABELS[c] for c in categories])
    ax.set_ylim(0, 110)
    ax.legend(loc="upper right", framealpha=0.9)
    plt.tight_layout()

    path = output_dir / "fig4_model_comparison.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate benchmark charts")
    parser.add_argument("--suffix", default="", help="Suffix for input filename")
    args = parser.parse_args()

    data = load_results(args.suffix)
    aggregates = data["aggregates"]

    output_dir = PROJECT_ROOT / "reports" / "charts"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating charts...")

    p1 = fig1_category_hit_rates_per_combo(aggregates, output_dir)
    print(f"  {p1}")

    p2 = fig2_precision_recall_f1(aggregates, output_dir)
    print(f"  {p2}")

    p3 = fig3_backend_comparison(aggregates, output_dir)
    if p3:
        print(f"  {p3}")

    p4 = fig4_model_comparison_at_best_threshold(aggregates, output_dir)
    print(f"  {p4}")

    print(f"\nAll charts saved to: {output_dir}")


if __name__ == "__main__":
    main()
