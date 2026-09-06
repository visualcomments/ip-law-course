# SPDX-FileCopyrightText: 2026 visualcomments ip-law-course contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Извлечение причинно-следственных связей «поправка -> изменение нормы».

Прямая адаптация модуля top-papers-graph
`src/scireason/temporal/temporal_triplet_extractor.py`: там из текста научных
публикаций извлекались причинно-следственные связки между открытиями
(«X causes Y»), здесь из текстов законов, новелл и поправок извлекаются
причинно-следственные связки законодательной динамики:

    «поправка (ФЗ-N от даты) -> норма права изменена/дополнена/введена/...»

Реализованы два бэкенда (по аналогии с llm_triplets / cooccurrence):
1) `rule_based` — регулярные выражения по глаголам законодательной динамики;
2) `llm` — LLM-промпт, адаптированный из temporal_triplet_extractor.

Выход — список `AmendmentEvent`, который затем агрегируется в темпоральный
«закон-граф» (см. graph_builder).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .schemas import (
    AmendmentEvent,
    AmendmentType,
    canonicalize_predicate,
    norm_id,
)
from .corpus_loader import NormChunk, normalize_law

# Глаголы изменения нормы и их приоритет (сила сигнала), по аналогии с
# _predicate_strength в top-papers-graph.
AMENDMENT_VERBS: Dict[str, float] = {
    "признана_утратившей_силу": 1.0,
    "исключена": 1.0,
    "изложена_в_новой_редакции": 0.98,
    "изменена": 0.95,
    "дополнена": 0.9,
    "введена": 0.92,
    "уточнена": 0.7,
    "влечёт_изменение": 0.85,
    "требует_приведения_в_соответствие": 0.8,
    "отсылает_к": 0.5,
}

_STRONG_AMENDMENT_PREDICATES = set(AMENDMENT_VERBS.keys())

# Регэкспы «законодательной динамики»: (pattern, predicate, strength).
# Предикат задан явно для каждого паттерна, чтобы не зависеть от подстрок
# внутри регулярного выражения.
_AMEND_PATTERNS: List[Tuple[str, str, float]] = [
    # «Статья 146 признана утратившей силу»
    (r"(?P<art>Статья\s+[0-9]+[а-я]?.*?)\s+(?:признана\s+)?утратившей\s+силу",
     "признана_утратившей_силу", 1.0),
    (r"(?P<art>Статья\s+[0-9]+[а-я]?.*?)\s+признана\s+утратившей\s+силу",
     "признана_утратившей_силу", 1.0),
    # «...изложена в новой редакции»
    (r"(?P<art>Статья\s+[0-9]+[а-я]?.*?)\s+изложена\s+в\s+новой\s+редакции",
     "изложена_в_новой_редакции", 0.98),
    # «Статья 1229 изменена»
    (r"(?P<art>Статья\s+[0-9]+[а-я]?.*?)\s+изменена",
     "изменена", 0.95),
    # «Статья 1270 дополнена пунктом 2 ...»
    (r"(?P<art>Статья\s+[0-9]+[а-я]?.*?)\s+дополнена",
     "дополнена", 0.9),
    # «Вводится статья 1229.1»
    (r"(?:вводится|введена)\s+(?:статья|статьи|ст\.?)?\s*(?P<art>[0-9]+[а-я]?)",
     "введена", 0.92),
]

# Канонический список «каких норм касается поправка» — ссылки на статьи.
_ART_RE = re.compile(r"(?:стать[яеию]|ст\.?)\s*([0-9]+[а-я]?(?:\.[0-9]+)?)", re.I)


def _clean_entity(text: str) -> str:
    s = " ".join((text or "").split())
    return s.strip(" ,;:-.").strip()


def _first_article(text: str) -> Optional[str]:
    m = _ART_RE.search(text or "")
    if m:
        return f"ст.{m.group(1).lower()}"
    return None


def _parse_year(text: str) -> Optional[str]:
    m = re.search(r"(19\d{2}|20\d{2}|2100)(?:-(\d{2})(?:-(\d{2}))?)?", text or "")
    return m.group(1) if m else None


def rule_based_amendments_from_text(
    text: str,
    source_doc: str = "",
    source_law: str = "ГК РФ",
    default_year: Optional[int] = None,
) -> List[AmendmentEvent]:
    """Извлекает события изменения норм по регулярным выражениям."""
    found: List[AmendmentEvent] = []
    seen: set = set()
    for sentence in re.split(r"(?<=[\.;])", text or ""):
        sent = " ".join(sentence.split())
        if not sent:
            continue
        year = _parse_year(sent) or (str(default_year) if default_year else None)
        for pat, pred_label, strength in _AMEND_PATTERNS:
            for m in re.finditer(pat, sent, flags=re.I):
                raw_art = _clean_entity(m.group("art")) if "art" in m.groupdict() else ""
                art = _first_article(raw_art) or _first_article(sent)
                if not art:
                    continue
                pred = canonicalize_predicate(pred_label)
                law = normalize_law(source_law)
                nid = norm_id(law, art)
                ev = AmendmentEvent(
                    subject=nid,
                    predicate=pred,
                    object=f"{law} (поправка)",
                    ts_start=year,
                    ts_end=year,
                    granularity="year" if year else "year",
                    source_doc=source_doc or "synthetic",
                    evidence_quote=sent[:200],
                    confidence=strength,
                    event_type="extracted",
                )
                key = ev.pair_key() + (ev.ts_start or "",)
                if key in seen:
                    continue
                seen.add(key)
                found.append(ev)
    return found


def amendments_from_structured(
    amendments: List[Dict[str, Any]],
    source="structured",
) -> List[AmendmentEvent]:
    """Конвертирует структурированные записи о поправках в AmendmentEvent.

    Формат записи (см. corpus_loader.SYNTHETIC_AMENDMENTS):
        {"law","article","clause","pred","year","src","note"}
    """
    out: List[AmendmentEvent] = []
    for a in amendments:
        law = normalize_law(str(a.get("law", "ГК РФ")))
        art = str(a.get("article", ""))
        clause = str(a.get("clause", ""))
        pred = canonicalize_predicate(a.get("pred", "изменена"))
        year = str(a.get("year", ""))[:4] or None
        nid = norm_id(law, art, clause)
        note = str(a.get("note", ""))
        out.append(
            AmendmentEvent(
                subject=nid,
                predicate=pred,
                object=f"{law} (поправка: {a.get('src','')})".strip(),
                ts_start=year,
                ts_end=year,
                granularity="year",
                source_doc=str(a.get("src", "")) or source,
                evidence_quote=note[:200] if note else None,
                confidence=AMENDMENT_VERBS.get(pred, 0.9),
                event_type="extracted",
            )
        )
    return out


def influence_from_structured(influence: List[Dict[str, Any]]) -> List[AmendmentEvent]:
    """Конвертирует причинно-следственные связи норм в AmendmentEvent.

    Связь «норма A отсылает_к норме B» моделируется как влияние нормы A на
    норму B (предикат из множества INFLUENCE).
    """
    out: List[AmendmentEvent] = []
    for c in influence:
        from_law = normalize_law(str(c.get("from_law", "ГК РФ")))
        from_art = str(c.get("from_article", ""))
        to_law = normalize_law(str(c.get("to_law", "ГК РФ")))
        to_art = str(c.get("to_article", ""))
        pred = canonicalize_predicate(c.get("pred", "отсылает_к"))
        a = norm_id(from_law, from_art)
        b = norm_id(to_law, to_art)
        out.append(
            AmendmentEvent(
                subject=a,
                predicate=pred,
                object=b,
                ts_start=None,
                granularity="year",
                source_doc="synthetic-influence",
                evidence_quote=str(c.get("linked", "")),
                confidence=AMENDMENT_VERBS.get(pred, 0.5),
                event_type="extracted",
            )
        )
    return out


# ---------------------------------------------------------------------------
# LLM-промпт (адаптация temporal_triplet_extractor)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Ты — исследователь норм российского права.
Задача: извлечь из фрагмента правового текста проверяемые причинно-следственные связи в виде триплетов (subject–predicate–object) о ДИНАМИКЕ НОРМ ПРАВА.

Что считается валидным триплетом:
- Внесение поправки в закон, которое изменяет норму права: (норма, тип_изменения, источник_поправки, дата).
- Причинно-следственная связь между нормами: одна норма влечёт изменение другой, требует приведения в соответствие, отсылает к другой.
- Норма права идентифицируется как «НазваниеЗакона ст.№» (например «ГК РФ ст.1229»), при необходимости с пунктом «/п.1».
- Дата (год как минимум) обязательна, если она есть в тексте.

Допустимые предикаты (канонический список):
изменена, дополнена, введена, изложена_в_новой_редакции, признана_утратившей_силу, исключена, уточнена, отсылает_к, влечёт_изменение, требует_приведения_в_соответствие.

Что НЕ является валидным триплетом:
- Простое упоминание нормы без явного факта её изменения или связи с другой нормой.
- Структура документа («раздел 1 описывает...»).
- Числовые параметры без правовой динамики.

Формат ответа — JSON-список:
[{"subject": "ГК РФ ст.1270", "predicate": "дополнена", "object": "ФЗ-35 от 12.03.2014", "year": "2014", "confidence": 0.9, "evidence": "..."}]
Лучше вернуть 1-2 точных триплета, чем 5 сомнительных."""


def build_llm_prompt(domain: str, chunk_text: str, context: Optional[str] = None) -> Tuple[str, str]:
    """Возвращает (system, user) промпт для LLM-извлечения связей поправок."""
    context_block = f"Контекст (документ корпуса):\n{context}\n\n" if context else ""
    user = f"""{context_block}Фрагмент правового текста:
{chunk_text}

Извлеки до 5 триплетов причинно-следственных связей «внесение поправки -> изменение нормы права» из этого фрагмента. Используй канонические предикаты из списка."""
    return SYSTEM_PROMPT, user


def parse_llm_response(text: str) -> List[AmendmentEvent]:
    """Парсит JSON-ответ LLM в список AmendmentEvent."""
    text = (text or "").strip()
    # вытащить JSON-массив, если LLM обернула в ```json ... ```
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except Exception:
        return []
    out: List[AmendmentEvent] = []
    for d in data if isinstance(data, list) else []:
        subj = str(d.get("subject", "")).strip()
        pred = canonicalize_predicate(d.get("predicate", ""))
        obj = str(d.get("object", "")).strip()
        year = str(d.get("year", ""))[:4] or None
        if not subj or not pred:
            continue
        out.append(
            AmendmentEvent(
                subject=subj,
                predicate=pred,
                object=obj,
                ts_start=year,
                ts_end=year,
                granularity="year",
                source_doc="llm",
                evidence_quote=str(d.get("evidence", ""))[:200],
                confidence=float(d.get("confidence", 0.6)),
                event_type="extracted",
            )
        )
    return out
