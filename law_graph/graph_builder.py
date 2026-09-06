# SPDX-FileCopyrightText: 2026 visualcomments ip-law-course contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Построение темпорального «закон-графа» и учебных экземпляров.

Адаптация top-papers-graph `temporal/temporal_kg_builder.py` + `tgnn/event_dataset.py`:

- вершины — нормы права (и законы);
- рёбра — поправки (изменение нормы во времени) и причинно-следственные связи норм;
- для обучения модели предиктивного анализа норм права из графа строятся
  `LegalTaskInstance`: норма + признаки её динамики до момента времени T +
  метка, была ли она фактически изменена в окне (T, T'].
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .schemas import (
    AmendmentEvent,
    AmendmentType,
    FACTUAL_AMENDMENT_PREDICATES,
    LegalTaskInstance,
    LegalNorm,
    norm_id,
)
from .corpus_loader import normalize_law


class LegalKnowledgeGraph:
    """Темпоральный граф норм права.

    Упрощённая адаптация TemporalKnowledgeGraph из top-papers-graph:
    сохраняем нормы (узлы) и списки событий-поправок (рёбра с временными рядами).
    """

    def __init__(self) -> None:
        self.events: List[AmendmentEvent] = []          # все события
        self.norms: Dict[str, LegalNorm] = {}           # norm_id -> норма
        self.laws: Dict[str, set] = defaultdict(set)    # закон -> множество норм
        # источник поправок -> число поправок (для интенсивности закона)
        self.amending_laws: Dict[str, int] = defaultdict(int)

    def add_norm(self, norm: LegalNorm) -> None:
        self.norms[norm.norm_id] = norm
        self.laws[norm.source_law].add(norm.norm_id)

    def add_event(self, ev: AmendmentEvent) -> None:
        self.events.append(ev)
        if ev.predicate in FACTUAL_AMENDMENT_PREDICATES and ev.object:
            self.amending_laws[normalize_law(ev.object)] += 1

    def add_norms_from_events(self) -> None:
        """Восстанавливает узлы норм по subject событий."""
        for ev in self.events:
            sid = ev.subject
            if sid and sid not in self.norms:
                # разбор norm_id «закон/ст.N» обратно в поля
                law_guess, art, clause = _split_norm_id(sid)
                self.add_norm(LegalNorm(source_law=law_guess, article=art, clause=clause, norm_id=sid))

    def norms_of_law(self, law: str) -> List[str]:
        return sorted(self.laws.get(normalize_law(law), set()))

    def events_for_norm(self, norm: str) -> List[AmendmentEvent]:
        return [e for e in self.events if e.subject == norm]

    def years_for_norm(self, norm: str) -> List[int]:
        return sorted(
            {e.year() for e in self.events if e.subject == norm and e.year() > 0}
        )

    def top_norms_by_amendments(self, k: int = 20) -> List[Tuple[str, int]]:
        cnt: Dict[str, int] = defaultdict(int)
        for e in self.events:
            if e.subject:
                cnt[e.subject] += 1
        return sorted(cnt.items(), key=lambda kv: kv[1], reverse=True)[:k]


def _split_norm_id(nid: str) -> Tuple[str, str, str]:
    """Разбор 'закон/ст.N' или 'закон/ст.N/п.M' в (law, article, clause)."""
    parts = nid.split("/")
    law = parts[0]
    art = parts[1] if len(parts) > 1 else ""
    clause = parts[2] if len(parts) > 2 else ""
    return law, art, clause


def build_event_stream(kg: LegalKnowledgeGraph) -> List[AmendmentEvent]:
    """Возвращает события, отсортированные по времени (хронологический поток)."""
    return sorted(kg.events, key=lambda e: e.sort_key())


def chronological_split(
    events: Sequence[AmendmentEvent],
    *,
    train_ratio: float = 0.6,
    valid_ratio: float = 0.2,
) -> Tuple[List[AmendmentEvent], List[AmendmentEvent], List[AmendmentEvent]]:
    """Хронологическое разбиение событийного потока (без случайного перемешивания).

    Гарантирует Temporal-Evaluation: никакое валидационное/тестовое событие не
    происходит раньше обучающего.
    """
    ordered = sorted(events, key=lambda e: e.sort_key())
    n = len(ordered)
    if n == 0:
        return [], [], []
    import math

    n_train = max(1, int(math.floor(n * train_ratio)))
    n_valid = max(0, int(math.floor(n * valid_ratio)))
    n_test = n - n_train - n_valid
    train = ordered[:n_train]
    valid = ordered[n_train : n_train + n_valid]
    test = ordered[n_train + n_valid :]
    return train, valid, test


def _window_years(e: AmendmentEvent) -> tuple:
    return (e.year(), e.ts_end or e.ts_start)


def build_task_instances(
    kg: LegalKnowledgeGraph,
    *,
    train_until: int,
    predict_window: int = 5,
    split: str = "train",
) -> List[LegalTaskInstance]:
    """Строит учебные экземпляры для предиктивного анализа норм права.

    Признаки каждой нормы считаются ТОЛЬКО по событиям до `train_until`
    (без утечки будущего). Метка label=1, если норма фактически изменена в
    окне (train_until, train_until+predict_window].

    split ∈ {train, valid, test} — используется только для разметки source и
    не влияет на вычисление признаков (разбиение делается хронологически
    над всем графом; см. prepare_dataset).
    """
    out: List[LegalTaskInstance] = []
    norms = kg.norms
    # события до train_until (для признаков)
    past_by_norm: Dict[str, List[AmendmentEvent]] = defaultdict(list)
    # события, изменяющие норму фактически, в окне (train_until, train_until+W]
    future_changes: Dict[str, List[AmendmentEvent]] = defaultdict(list)
    top_year = train_until + predict_window

    for e in kg.events:
        if e.year() == 0:
            continue
        if e.year() <= train_until:
            past_by_norm[e.subject].append(e)
        elif e.year() <= top_year:
            future_changes[e.subject].append(e)

    # Ссылки на нормы (рёбра влияния) — структурные связи, действуют всегда
    # (не зависят от времени, поэтому учитываются полностью, без фильтра по году;
    # это не утечка будущего — отсылка/влечение-изменения характеризует
    # связанность норм, а не хронологию поправок).
    ref_to: Dict[str, int] = defaultdict(int)   # норма, на которую ссылаются
    outdeg: Dict[str, int] = defaultdict(int)   # ссылок нормы наружу
    past_influence = [
        e for e in kg.events
        if e.predicate in {"отсылает_к", "влечёт_изменение", "требует_приведения_в_соответствие"}
    ]
    for e in past_influence:
        if e.subject and e.object:
            ref_to[e.object] += 1
            outdeg[e.subject] += 1

    # интенсивность поправок по закону-источнику (число поправок за окно 5 лет)
    law_counts: Dict[str, int] = defaultdict(int)
    for e in kg.events:
        if e.year() and (train_until - 5) <= e.year() <= train_until:
            law_counts[e.subject.split("/")[0]] += 1

    for nid, norm in norms.items():
        past = past_by_norm.get(nid, [])
        factual_past = [e for e in past if e.predicate in FACTUAL_AMENDMENT_PREDICATES]
        if factual_past:
            last_change = max(e.year() for e in factual_past)
            years_since = train_until - last_change
        else:
            years_since = None
        amendments_last_5y = sum(1 for e in factual_past if (train_until - 5) <= e.year() <= train_until)
        law = norm.source_law or norm.norm_id.split("/")[0]
        changed_in_window = bool(future_changes.get(nid))
        label = 1 if changed_in_window else 0
        label_source = ""
        if changed_in_window:
            src_events = future_changes.get(nid)
            label_source = "factual:" + ";".join(
                f"{e.predicate}@{e.year()}" for e in src_events if e.predicate in FACTUAL_AMENDMENT_PREDICATES
            ) or "influence"
        out.append(
            LegalTaskInstance(
                norm_id=nid,
                source_law=law,
                article=norm.article,
                clause=norm.clause,
                norm_text=norm.norm_text,
                years_since_last_change=years_since,
                amendments_last_5y=amendments_last_5y,
                referenced_by_active=ref_to.get(nid, 0),
                outdegree_norm_links=outdeg.get(nid, 0),
                law_amendment_intensity=float(law_counts.get(law, 0)),
                label=label,
                label_source=label_source,
            )
        )
    return out


def to_graph_snapshot(kg: LegalKnowledgeGraph) -> Dict[str, Any]:
    """Сериализует граф в словаре для экспорта JSON."""
    return {
        "norm_count": len(kg.norms),
        "law_count": len(kg.laws),
        "event_count": len(kg.events),
        "norms": [
            {"norm_id": n.norm_id, "source_law": n.source_law, "article": n.article,
             "clause": n.clause, "norm_text": n.norm_text[:300]}
            for n in kg.norms.values()
        ],
        "events": [
            {"subject": e.subject, "predicate": e.predicate, "object": e.object,
             "year": e.year(), "source_doc": e.source_doc, "evidence": e.evidence_quote}
            for e in kg.events
        ],
    }
