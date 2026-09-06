# SPDX-FileCopyrightText: 2026 visualcomments ip-law-course contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Предиктивная модель: какие нормы права вероятно будут изменены.

Адаптация top-papers-graph `tgnn/tgn_link_prediction.py`: там темпоральный
граф знаний научных публикаций прогнозировал новые связи между открытиями.
Здесь «закон-граф» норм и поправок используется, чтобы предсказать, какие
нормы права с наибольшей вероятностью будут изменены в ближайшем окне.

Реализованы два бэкенда:
1) `heuristic` — детерминированный скоринг признаков динамики норм
   (рекуррентность поправок, общие соседи по влиянию, память узла, давность
   последней поправки) — работает без внешних зависимостей;
2) `pyg` — опционально реальная TGN-память PyTorch Geometric (если установлена).

Выход — ранжированный список (norm_id, score): норма, которая скорее всего
будет изменена.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import exp
from typing import DefaultDict, Dict, List, Optional, Sequence, Tuple

from .schemas import AmendmentEvent, FACTUAL_AMENDMENT_PREDICATES

try:  # pragma: no cover
    import torch
    import torch.nn.functional as F
    from torch_geometric.nn.models.tgn import IdentityMessage, LastAggregator, TGNMemory
except Exception:  # pragma: no cover
    torch = None
    F = None
    IdentityMessage = None
    LastAggregator = None
    TGNMemory = None


@dataclass(frozen=True)
class LegalLinkPredConfig:
    """Гиперпараметры скоринга динамики норм (аналог TGNLinkPredConfig)."""

    recent_window_years: int = 5       # окно «недавних» поправок
    recency_half_life_years: float = 3.0
    repeat_weight: float = 0.40        # частые повторные поправки -> выше шанс новой
    influence_weight: float = 0.35     # нормы, на которые влияют другие, более «горячие»
    neighbor_memory_weight: float = 0.25
    law_intensity_weight: float = 0.15 # нормы в «законе-под-редактированием» выше
    min_score: float = 0.02
    decay_for_history_years: float = 20.0
    memory_dim: int = 64
    time_dim: int = 16
    backend: str = "auto"  # auto|heuristic|pyg


def pyg_available() -> bool:
    return all(x is not None for x in (torch, F, IdentityMessage, LastAggregator, TGNMemory))


def _safe_year(ts: Optional[str]) -> int:
    try:
        return int(str(ts)[:4])
    except Exception:
        return 0


def _decay(delta_years: int, half_life: float) -> float:
    if delta_years <= 0:
        return 1.0
    hl = max(0.1, float(half_life))
    return exp(-0.6931471805599453 * float(delta_years) / hl)


class LegalChangeHeuristic:
    """Детерминированный скоринг вероятности изменения нормы.

    Для каждой нормы накопливаются фактические события изменения (поправки) и
    рёбра влияния (отсылки/влечёт_изменение). Скоринг использует:
      recency-память (недавние поправки), повторяемость (норма часто меняется),
      влиятельность (сколько других норм на неё ссылаются/влекут её изменение),
      интенсивность закона (поправки в этом законе в недавнем окне),
      давность последней поправки (для baseline-признаков).
    """

    def __init__(self, events: Sequence[AmendmentEvent], config: Optional[LegalLinkPredConfig] = None):
        self.config = config or LegalLinkPredConfig()
        self.events = [e for e in events if e.year() > 0]
        self.years = sorted({e.year() for e in self.events})
        self.current_year = max(self.years) if self.years else 0
        self._build()

    def _build(self) -> None:
        cfg = self.config
        self.amend: DefaultDict[str, List[int]] = defaultdict(list)  # norm -> years of factual change
        self.influence_to: DefaultDict[str, List[Tuple[str, int]]] = defaultdict(list)
        self.law_years: DefaultDict[str, List[int]] = defaultdict(list)  # law -> change years
        for e in self.events:
            y = e.year()
            law = e.subject.split("/")[0] if e.subject else ""
            if e.predicate in FACTUAL_AMENDMENT_PREDICATES:
                self.amend[e.subject].append(y)
                if law:
                    self.law_years[law].append(y)
            else:
                # рёбра влияния норм: subject влияет на object
                src, dst = e.subject, e.object
                if src and dst:
                    self.influence_to[dst].append((src, y))

    def norm_law(self, nid: str) -> str:
        return nid.split("/")[0]

    def feature_dict(self, nid: str) -> Dict[str, float]:
        cfg = self.config
        cy = self.current_year
        amend_years = self.amend.get(nid, [])
        last_change = max(amend_years) if amend_years else None
        years_since = (cy - last_change) if last_change is not None else None

        # 1) recency-память: взвешенная сумма поправок с распадом по времени
        recency = sum(_decay(cy - y, cfg.recency_half_life_years) for y in amend_years)

        # 2) повторяемость в недавнем окне
        recent_thr = cy - cfg.recent_window_years
        repeat = sum(1 for y in amend_years if y >= recent_thr)

        # 3) влиятельность: сколько норм на неё ссылаются/влекут её изменение (с распадом)
        influence = sum(_decay(cy - y, cfg.recency_half_life_years) for _src, y in self.influence_to.get(nid, []))

        # 4) интенсивность закона: поправок в этом законе за недавнее окно
        law = self.norm_law(nid)
        law_recent = sum(1 for y in self.law_years.get(law, []) if y >= recent_thr)

        # 5) давность последней поправки (чем дольше не менялась — тем «созрела»)
        staleness = 0.0
        if years_since is not None:
            staleness = min(1.0, years_since / cfg.decay_for_history_years)

        return {
            "recency": recency,
            "repeat": float(repeat),
            "influence": influence,
            "law_intensity": float(law_recent),
            "staleness": staleness,
            "years_since_last_change": float(years_since) if years_since is not None else 0.0,
        }

    def score(self, nid: str) -> float:
        cfg = self.config
        f = self.feature_dict(nid)
        if f["repeat"] == 0 and f["influence"] == 0 and f["recency"] == 0:
            return 0.0
        raw = (
            cfg.repeat_weight * f["repeat"]
            + cfg.influence_weight * f["influence"]
            + cfg.neighbor_memory_weight * f["recency"]
            + cfg.law_intensity_weight * f["law_intensity"]
        )
        # нормализация
        norm = 1.0 + float(f["repeat"]) + float(f["influence"]) + float(f["law_intensity"])
        score = raw / norm
        # мягко повысить «созревшие» нормы (давно не менявшиеся, но активно связанные)
        score = score * (0.7 + 0.3 * f["staleness"])
        return score

    def rank(self, top_k: int = 30) -> List[Tuple[str, float]]:
        cfg = self.config
        norms = set(self.amend.keys()) | set(self.influence_to.keys())
        scored = []
        for nid in norms:
            s = self.score(nid)
            if s >= cfg.min_score:
                scored.append((nid, s))
        scored.sort(key=lambda kv: kv[1], reverse=True)
        return scored[:top_k]


def legal_link_prediction(
    events: Sequence[AmendmentEvent],
    *,
    top_k: int = 30,
    config: Optional[LegalLinkPredConfig] = None,
) -> List[Tuple[str, float]]:
    """Возвращает ранг норм, которые с наибольшей вероятностью будут изменены.

    Аналог tgn_link_prediction, но выход — список (norm_id, score), где score
    интерпретируется как вероятность/уверенность будущего изменения нормы.
    """
    cfg = config or LegalLinkPredConfig()
    backend = str(cfg.backend or "auto").lower()
    if backend in {"auto", "pyg"} and pyg_available():
        try:
            return _pyg_legal_change_prediction(events, top_k=top_k, cfg=cfg)
        except Exception:
            if backend == "pyg":
                raise
    h = LegalChangeHeuristic(events, config=cfg)
    return h.rank(top_k)


def _pyg_legal_change_prediction(
    events: Sequence[AmendmentEvent],
    *,
    top_k: int,
    cfg: LegalLinkPredConfig,
) -> List[Tuple[str, float]]:
    """Опциональный PyG TGN-memory прогноз изменения норм.

    Нормы = узлы графа; события поправок подаются в TGNMemory как сообщения;
    изменения в памяти дают скрытые представления, по которым оценивается
    вероятность будущей поправки нормы.
    """
    if not pyg_available():
        raise RuntimeError("PyG TGN backend is not available")
    ordered = sorted(events, key=lambda e: e.sort_key())
    nodes = sorted({e.subject for e in ordered if e.subject})
    if len(nodes) < 2:
        return []
    node_to_idx = {n: i for i, n in enumerate(nodes)}

    device = torch.device("cpu")
    memory = TGNMemory(
        num_nodes=len(nodes),
        raw_msg_dim=2,
        memory_dim=cfg.memory_dim,
        time_dim=cfg.time_dim,
        message_module=IdentityMessage(2, cfg.memory_dim, cfg.time_dim),
        aggregator_module=LastAggregator(),
    ).to(device)
    memory.reset_state()
    memory.train()

    last_t = 0
    changed = set()
    for ev in ordered:
        if not ev.subject:
            continue
        src = torch.tensor([node_to_idx[ev.subject]], dtype=torch.long, device=device)
        dst = src  # событие изменения нормы — «самопетля» во времени
        t_num = _safe_year(ev.ts_start or ev.ts_end)
        last_t = max(last_t, t_num)
        t = torch.tensor([t_num], dtype=torch.long, device=device)
        raw = torch.tensor(
            [[float(ev.confidence), float(max(ev.weight, 1.0))]],
            dtype=torch.float32, device=device,
        )
        memory.update_state(src, dst, t, raw)
        if ev.predicate in FACTUAL_AMENDMENT_PREDICATES:
            changed.add(ev.subject)

    memory.eval()
    n_id = torch.arange(len(nodes), device=device)
    z, _last = memory(n_id)
    z = F.normalize(z, p=2.0, dim=-1)
    # «горячесть» узла = величина изменения памяти (евклидова норма скрытого вектора)
    scores = torch.norm(z, dim=-1)
    order = torch.argsort(scores, descending=True)
    out = []
    for idx in order.tolist():
        nid = nodes[idx]
        if nid not in changed:
            continue
        out.append((nid, float(scores[idx].item())))
        if len(out) >= top_k:
            break
    return out
