"""
backend/evaluation/stats.py — Bootstrap statistical aggregation and paired comparisons.

Rules:
- 95% bootstrap CI (2000 resamples, seeded, numpy).
- Macro-average per metric over the items where the metric applies; always record n.
- Paired comparison: mean delta with paired bootstrap CI, wins/losses/ties.
- Verdict: "difference not distinguishable from zero" when the CI contains 0.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np


def bootstrap_ci(
    values: List[float],
    n_resamples: int = 2000,
    seed: int = 42,
    confidence_level: float = 0.95,
) -> Dict[str, Any]:
    """
    Compute mean and two-sided bootstrap confidence interval for a list of metric values.
    """
    if not values:
        return {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0}

    arr = np.array(values, dtype=float)
    n = len(arr)
    mean_val = float(np.mean(arr))

    if n == 1 or np.all(arr == arr[0]):
        return {
            "mean": round(mean_val, 4),
            "ci_low": round(mean_val, 4),
            "ci_high": round(mean_val, 4),
            "n": n,
        }

    rng = np.random.default_rng(seed)
    indices = rng.integers(0, n, size=(n_resamples, n))
    resampled_means = np.mean(arr[indices], axis=1)

    alpha = (1.0 - confidence_level) / 2.0
    ci_low = float(np.percentile(resampled_means, alpha * 100))
    ci_high = float(np.percentile(resampled_means, (1.0 - alpha) * 100))

    return {
        "mean": round(mean_val, 4),
        "ci_low": round(ci_low, 4),
        "ci_high": round(ci_high, 4),
        "n": n,
    }


def paired_bootstrap_comparison(
    values_a: List[float],
    values_b: List[float],
    n_resamples: int = 2000,
    seed: int = 42,
    confidence_level: float = 0.95,
    eps: float = 1e-6,
) -> Dict[str, Any]:
    """
    Paired comparison of two runs on identical items.
    delta = values_a - values_b
    """
    if len(values_a) != len(values_b):
        raise ValueError(f"Mismatched paired lengths: {len(values_a)} vs {len(values_b)}")

    n = len(values_a)
    if n == 0:
        return {
            "mean_a": 0.0,
            "mean_b": 0.0,
            "mean_delta": 0.0,
            "ci_low": 0.0,
            "ci_high": 0.0,
            "wins": 0,
            "losses": 0,
            "ties": 0,
            "verdict": "no data",
            "n": 0,
        }

    a = np.array(values_a, dtype=float)
    b = np.array(values_b, dtype=float)
    deltas = a - b

    mean_a = float(np.mean(a))
    mean_b = float(np.mean(b))
    mean_delta = float(np.mean(deltas))

    wins = int(np.sum(deltas > eps))
    losses = int(np.sum(deltas < -eps))
    ties = int(np.sum(np.abs(deltas) <= eps))

    if n == 1 or np.all(deltas == deltas[0]):
        ci_low = mean_delta
        ci_high = mean_delta
    else:
        rng = np.random.default_rng(seed)
        indices = rng.integers(0, n, size=(n_resamples, n))
        resampled_deltas = np.mean(deltas[indices], axis=1)

        alpha = (1.0 - confidence_level) / 2.0
        ci_low = float(np.percentile(resampled_deltas, alpha * 100))
        ci_high = float(np.percentile(resampled_deltas, (1.0 - alpha) * 100))

    if ci_low <= 0.0 <= ci_high:
        verdict = "difference not distinguishable from zero"
    elif ci_low > 0:
        verdict = "variant A higher than variant B"
    else:
        verdict = "variant A lower than variant B"

    return {
        "mean_a": round(mean_a, 4),
        "mean_b": round(mean_b, 4),
        "mean_delta": round(mean_delta, 4),
        "ci_low": round(ci_low, 4),
        "ci_high": round(ci_high, 4),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "verdict": verdict,
        "n": n,
    }

