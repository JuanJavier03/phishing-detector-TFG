from __future__ import annotations

"""
Adapta la libreria pymcdm TOPSIS a las necesidades del proyecto, incluyendo normalizacion segura ante columnas nulas.
"""

from math import sqrt
from typing import Any, List, Sequence
import warnings

import numpy as np
from pymcdm.methods import TOPSIS


def _safe_vector_normalization(values: np.ndarray, cost: bool = False) -> np.ndarray:
    norm = sqrt(float(np.sum(values ** 2)))
    if norm == 0.0:
        return np.zeros_like(values, dtype=float)
    normalized = values / norm
    if cost:
        return 1.0 - normalized
    return normalized


def topsis_scores_with_library(
    matrix: Sequence[Sequence[Any]],
    weights: Sequence[float],
    criteria_types: Sequence[int] | None = None,
) -> List[float]:
    if not matrix:
        return []

    decision_matrix = np.asarray(matrix, dtype=float)
    criteria_weights = np.asarray(weights, dtype=float)
    criteria_type_values = (
        np.ones(decision_matrix.shape[1], dtype=int)
        if criteria_types is None
        else np.asarray(criteria_types, dtype=int)
    )

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="invalid value encountered in divide",
            category=RuntimeWarning,
        )
        raw_scores = TOPSIS(normalization_function=_safe_vector_normalization)(
            decision_matrix,
            criteria_weights,
            criteria_type_values,
            validation=False,
        )

    scores: List[float] = []
    for score in raw_scores:
        value = float(score)
        if value != value:
            scores.append(0.5)
        else:
            scores.append(round(value, 6))
    return scores


__all__ = ["topsis_scores_with_library"]
