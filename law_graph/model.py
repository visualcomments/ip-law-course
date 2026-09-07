# SPDX-FileCopyrightText: 2026 visualcomments ip-law-course contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Обучаемая модель предиктивного анализа норм права.

Над признаками LegalTaskInstance обучается лёгкий классификатор, который
предсказывает вероятность изменения нормы (label=1) в будущем окне. Это
«модель» в конвейере, параллельная скорингу на графе из link_prediction:
- link_prediction.LegalChangeHeuristic — объяснимый скоринг без обучения;
- model.fit_model — обучаемая логистическая/градиентная модель по признакам.

Модель строится на numpy (без тяжёлых зависимостей), чтобы запускаться
офлайн в любом окружении курса.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, List, Optional, Sequence

try:  # pragma: no cover
    import numpy as np
except Exception:  # pragma: no cover
    np = None


FEATURE_NAMES = [
    "years_since_last_change",
    "amendments_last_5y",
    "referenced_by_active",
    "outdegree_norm_links",
    "law_amendment_intensity",
]


def feature_vector(inst) -> List[float]:
    return [
        float(inst.years_since_last_change if inst.years_since_last_change is not None else 0.0),
        float(inst.amendments_last_5y),
        float(inst.referenced_by_active),
        float(inst.outdegree_norm_links),
        float(inst.law_amendment_intensity),
    ]


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


@dataclass
class TrainedModel:
    """Возвращаемая обученная модель: веса, признаки и свободный член (bias)."""

    weights: Dict[str, float]
    bias: float
    features: List[str]

    def predict_proba(self, inst) -> float:
        z = self.bias
        fv = dict(zip(self.features, feature_vector(inst)))
        for name in self.features:
            z += self.weights.get(name, 0.0) * fv.get(name, 0.0)
        return _sigmoid(z)


def fit_model(
    instances: Sequence,
    *,
    lr: float = 0.1,
    epochs: int = 300,
    l2: float = 1e-3,
    seed: int = 7,
    labels_available: bool = True,
) -> TrainedModel:
    """Логистическая регрессия на признаках динамики норм (GD).

    Если numpy доступен — векторизованная реализация; иначе — скалярный GD.
    """
    feats = FEATURE_NAMES
    rows = [feature_vector(i) for i in instances]
    if labels_available:
        ys = [float(int(i.label or 0)) for i in instances]
    else:
        ys = [0.0] * len(rows)

    if np is not None:
        X = np.array(rows, dtype=float)
        y = np.array(ys, dtype=float)
        n, d = X.shape
        # стандартизация
        mu = X.mean(axis=0)
        sd = X.std(axis=0) + 1e-9
        Xs = (X - mu) / sd
        w = np.zeros(d, dtype=float)
        b = 0.0
        for _ in range(epochs):
            z = Xs @ w + b
            p = 1.0 / (1.0 + np.exp(-np.clip(z, -20, 20)))
            grad = (p - y)
            w -= lr * ((Xs.T @ grad) / n + l2 * w)
            b -= lr * (grad.sum() / n)
        # возврат в исходный масштаб
        w_scaled = w / sd
        b_final = b - float((w / sd) @ mu)
        weights = {name: float(w_scaled[i]) for i, name in enumerate(feats)}
        return TrainedModel(weights=weights, bias=float(b_final), features=feats)

    # scalar fallback (без numpy)
    w = {f: 0.0 for f in feats}
    b = 0.0
    for _ in range(epochs):
        gb = 0.0
        gw = {f: 0.0 for f in feats}
        for xi, yi in zip(rows, ys):
            z = b + sum(w[f] * xi[i] for i, f in enumerate(feats))
            p = _sigmoid(z)
            err = p - yi
            gb += err
            for i, f in enumerate(feats):
                gw[f] += err * xi[i]
        for f in feats:
            w[f] -= lr * (gw[f] / len(rows) + l2 * w[f])
        b -= lr * (gb / len(rows))
    return TrainedModel(weights=w, bias=b, features=feats)


def evaluate_predictions(
    instances: Sequence,
    scores: Sequence[float],
) -> Dict[str, float]:
    """Метрики: AUC-ROC, точность (precision) в top-k, доля верных ответов (accuracy).

    instances — с метками label; scores — вероятность изменения.
    """
    if np is None:
        return {"auc_roc": float("nan"), "prec_at_5": float("nan"),
                "prec_at_10": float("nan"), "accuracy": float("nan")}
    y = np.array([int(i.label or 0) for i in instances], dtype=float)
    s = np.array([float(x) for x in scores], dtype=float)
    n = len(y)
    if n == 0:
        return {"auc_roc": 0.0, "prec_at_5": 0.0, "prec_at_10": 0.0, "accuracy": 0.0}

    # accuracy at 0.5
    acc = float(np.mean((s >= 0.5).astype(float) == y))

    # AUC-ROC (простая реализация)
    order = np.argsort(-s)
    y_sorted = y[order]
    n_pos = int(y_sorted.sum())
    n_neg = n - n_pos
    auc = 0.0
    if n_pos > 0 and n_neg > 0:
        ranks = np.arange(1, n + 1)
        rank_sum_pos = float(ranks[y_sorted == 1].sum())
        auc = (rank_sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)

    def prec_at(k: int) -> float:
        k = min(k, n)
        top = y_sorted[:k]
        return float(top.mean()) if k else 0.0

    return {
        "auc_roc": round(auc, 4),
        "prec_at_5": round(prec_at(5), 4),
        "prec_at_10": round(prec_at(10), 4),
        "accuracy": round(acc, 4),
    }
