# SPDX-FileCopyrightText: 2026 visualcomments ip-law-course contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Адаптированная модель данных «закон-граф».

Адаптация модели top-papers-graph (TemporalTriplet / TemporalEvent) на область
российского права: вместо причинно-следственных связей между научными
открытиями строятся причинно-следственные связи вида «внесение поправки ->
изменение нормы права». Вершинами графа становятся нормы права
(статья / пункт / часть закона) и законы; событиями — поправки, меняющие нормы
во времени.

Назначение модели — предиктивный анализ норм права: по темпоральному графу
норм и внесённых поправок предсказать, какие нормы вероятно будут изменены.
"""
from __future__ import annotations

from hashlib import sha1
import json
import re
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Идентификация нормы права
# ---------------------------------------------------------------------------

# Стандартизированные «типы изменений» нормы права — предикаты, которые в
# top-papers-graph были причинно-следственными предикатами (causes, induces,
# leads_to, ...). Здесь они заменены на глаголы законодательной динамики.
AmendmentType = Literal[
    "изменена",                 # modified
    "дополнена",                # supplemented
    "введена",                  # newly introduced
    "изложена_в_новой_редакции",  # restated in new edition
    "признана_утратившей_силу",   # declared no longer in force
    "исключена",                # deleted
    "уточнена",                 # clarified
    "отсылает_к",               # cross-reference to another norm (norm->norm)
    "вероятно_будет_изменена",  # PREDICTION target predicate (future change)
]

# Канонический словарь синонимов -> стандартный предикат.
AMENDMENT_ALIASES: Dict[str, str] = {
    # изменена
    "изменена": "изменена",
    "изменена_редакция": "изменена",
    "изложена_в_редакции": "изменена",
    # дополнена
    "дополнена": "дополнена",
    "дополнена_пунктом": "дополнена",
    "добавлена_норма": "введена",
    "введена": "введена",
    "введена_статья": "введена",
    "добавлена": "введена",
    "изложена_в_новой_редакции": "изложена_в_новой_редакции",
    "в_новой_редакции": "изложена_в_новой_редакции",
    "новая_редакция": "изложена_в_новой_редакции",
    "признана_утратившей_силу": "признана_утратившей_силу",
    "признана_утратившей_силу_с": "признана_утратившей_силу",
    "утратила_силу": "признана_утратившей_силу",
    "исключена": "исключена",
    "исключена_из": "исключена",
    "уточнена": "уточнена",
    "уточнена_редакция": "уточнена",
    "отсылает_к": "отсылает_к",
    "ссылается_на": "отсылает_к",
    "влечёт_изменение": "влечёт_изменение",
    "требует_приведения_в_соответствие": "требует_приведения_в_соответствие",
    "вероятно_будет_изменена": "вероятно_будет_изменена",
}

# Предикаты, точно фиксирующие ФАКТ изменения нормы (для обучения/оценки).
FACTUAL_AMENDMENT_PREDICATES = {
    "изменена",
    "дополнена",
    "введена",
    "изложена_в_новой_редакции",
    "признана_утратившей_силу",
    "исключена",
    "уточнена",
}

# Предикаты причинно-следственного влияния норм друг на друга.
INFLUENCE_AMENDMENT_PREDICATES = {
    "отсылает_к",
    "влечёт_изменение",
    "требует_приведения_в_соответствие",
}


def _norm_fragment_key(text: str) -> Optional[str]:
    """Возвращает ключ «статья/пункт/часть» из строки-заголовка нормы.

    Ожидаемые формы: «Статья 1229», «п. 2 ст. 1270», «часть 4 статьи 1252 ГК РФ»,
    «ст. 146 УК РФ». Если норма не распознана — None.
    """
    if not text:
        return None
    s = " ".join(str(text).split())
    m = re.search(
        r"(?:стать[яеию]|ст\.?)\s*([0-9]+(?:[а-яА-Я])?)", s, flags=re.I
    )
    if m:
        return f"ст.{m.group(1).lower()}"
    m = re.search(
        r"пункт[а-я]?\s*([0-9]+)|п\.\s*([0-9]+)", s, flags=re.I
    )
    if m:
        return f"п.{m.group(1) or m.group(2)}"
    m = re.search(
        r"част[ьи]\s*([0-9]+)", s, flags=re.I
    )
    if m:
        return f"ч.{m.group(1)}"
    return None


def norm_id(source_law: str, article: str, clause: str = "") -> str:
    """Стабильный идентификатор нормы права.

    Пример: norm_id("ГК РФ", "ст.1229") -> "гк-рф/ст.1229"; с пунктом ->
    "гк-рф/ст.1229/п.1". Нижний регистр, слагизированные сегменты.
    """
    law = re.sub(r"[^a-zа-я0-9]+", "-", (source_law or "").lower()).strip("-")

    def _segment(part: str, default_prefix: str = "") -> str:
        """Нормализует «статья/пункт» в согласованный вид: 'ст.1229', 'п.2', 'ч.4'."""
        p = " ".join((part or "").strip().lower().split())
        if not p:
            return ""
        m = re.search(
            r"(ст\.?|статья|статьи)\s*([0-9]+[а-я]?(?:\.[0-9]+)?)", p, flags=re.I
        )
        if m:
            return f"ст.{m.group(2)}"
        m = re.search(r"(п\.?|пункт)\s*([0-9]+)", p, flags=re.I)
        if m:
            return f"п.{m.group(2)}"
        m = re.search(r"(ч\.?|часть)\s*([0-9]+)", p, flags=re.I)
        if m:
            return f"ч.{m.group(2)}"
        # простое число -> статья
        m = re.search(r"^[0-9]+[а-я]?(?:\.[0-9]+)?$", p)
        if m and default_prefix:
            return f"{default_prefix}{p}"
        return p

    art = _segment(article, default_prefix="ст.")
    base = f"{law}/{art}" if art else law
    if clause:
        cl = _segment(clause, default_prefix="п.")
        if cl:
            base = f"{base}/{cl}"
    if not base:
        base = f"norm-{sha1((source_law or '').encode('utf-8')).hexdigest()[:8]}"
    return base


class LegalNorm(BaseModel):
    """Норма права — вершина «закон-графа».

    Аналог «термина/сущности» в top-papers-graph, но здесь это конкретная норма
    права: статья / пункт / часть закона.
    """

    source_law: str = Field(description="Источник права, например «ГК РФ» / «УК РФ»")
    article: str = Field(default="", description="Статья/пункт/часть, например «ст.1229»")
    clause: str = Field(default="", description="Пункт/часть внутри статьи, например «п.1»")
    norm_text: str = Field(default="", description="Краткое содержание нормы (для контекста)")
    norm_id: str = Field(default="")

    @model_validator(mode="after")
    def _ensure_id(self) -> "LegalNorm":
        if not self.norm_id:
            self.norm_id = norm_id(self.source_law, self.article, self.clause)
        return self

    def as_text(self) -> str:
        head = f"{self.source_law} {self.article}".strip()
        if self.clause:
            head = f"{head} {self.clause.strip()}"
        body = f" — {self.norm_text}" if self.norm_text else ""
        return f"{head}{body}"


class AmendmentEvent(BaseModel):
    """Отдельное событие «внесение поправки -> изменение нормы».

    Прямой аналог TemporalEvent из top-papers-graph, но субъект/объект — нормы
    либо закон-источник, а предикат — тип изменения нормы во времени.

    Две семантики:
    - событие ФАКТА изменения: `subject`=норма, `predicate`=фактический глагол
      (изменена/дополнена/...), `object`=закон/поправка, которая это сделала;
    - событие ВЛИЯНИЯ норм: `subject`=норма A, `predicate`=(отсылает_к /
      влечёт_изменение), `object`=норма B.
    """

    event_id: Optional[str] = None
    subject: str = Field(description="Норма/закон — объект изменения (что меняется)")
    predicate: str = Field(description="Тип изменения (см. AmendmentType)")
    object: str = Field(default="", description="Источник поправки или норма-следствие")
    ts_start: Optional[str] = None  # дата поправки: YYYY / YYYY-MM / YYYY-MM-DD
    ts_end: Optional[str] = None
    granularity: str = "year"
    source_doc: str = Field(default="", description="Документ корпуса, откуда извлечено")
    evidence_quote: Optional[str] = None
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    event_type: str = "extracted"  # extracted | reviewed | corrected
    weight: float = 1.0

    def year(self) -> int:
        try:
            return int(str(self.ts_start or "")[:4])
        except Exception:
            return 0

    def time_key(self) -> str:
        start = self.ts_start or ""
        end = self.ts_end or start
        return f"{self.granularity}:{start}:{end}"

    def pair_key(self) -> tuple:
        return (
            self.subject.strip().lower(),
            self.predicate.strip().lower(),
            (self.object or "").strip().lower(),
        )

    def sort_key(self) -> tuple:
        return (self.ts_start or "", self.ts_end or "", self.subject.lower(), self.object.lower())

    def stable_id(self) -> str:
        if self.event_id:
            return self.event_id
        raw = (
            f"{self.subject}|{self.predicate}|{self.object}|"
            f"{self.ts_start or ''}|{self.ts_end or ''}|{self.source_doc}|{self.quote_norm()}"
        )
        return sha1(raw.encode("utf-8")).hexdigest()[:16]

    def quote_norm(self) -> str:
        return self.evidence_quote or ""

    def as_text(self) -> str:
        q = f" | evidence={self.evidence_quote}" if self.evidence_quote else ""
        return (
            f"{self.subject} | {self.predicate} | {self.object}"
            f" | {self.time_key()} | conf={self.confidence:.2f}{q}"
        )


class LegalTriplet(BaseModel):
    """Триплет причинно-следственной связи в праве.

    Аналог TemporalTriplet: (субъект, предикат, объект, время, источник).
    """

    subject: str
    predicate: str
    object: str
    time: Optional[Dict[str, Any]] = None  # {start, end, granularity}
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    source_doc: str = Field(default="")
    evidence_quote: Optional[str] = None

    def to_event(self) -> AmendmentEvent:
        ts = (self.time or {}).get("start") if self.time else None
        te = (self.time or {}).get("end") if self.time else None
        gran = (self.time or {}).get("granularity", "year") if self.time else "year"
        return AmendmentEvent(
            subject=self.subject,
            predicate=self.predicate,
            object=self.object,
            ts_start=ts,
            ts_end=te,
            granularity=gran,
            source_doc=self.source_doc,
            evidence_quote=self.evidence_quote,
            confidence=self.confidence,
        )


class LegalTaskInstance(BaseModel):
    """Учебный экземпляр для модели предиктивного анализа норм права.

    Формулировка задачи: дано состояние «закон-графа» (нормы и поправки) на
    момент времени T (train_until). Надо предсказать, будет ли норма `norm_id`
    изменена в окне (T, T'] (label=1) или нет (label=0).
    """

    norm_id: str
    source_law: str
    article: str
    clause: str = ""
    norm_text: str = ""
    # Признаки (вычисляются из графа до момента времени T — без утечки будущего)
    years_since_last_change: Optional[int] = None   # лет с последней поправки
    amendments_last_5y: int = 0                     # число поправок этой нормы за 5 лет
    referenced_by_active: int = 0                   # сколько действующих норм на неё ссылается
    outdegree_norm_links: int = 0                   # её ссылок на другие нормы
    law_amendment_intensity: float = 0.0            # интенсивность поправок в законе (= окне)
    predicted_score: Optional[float] = None         # выход модели (вероятность изменения)
    label: Optional[int] = None                     # 1 = фактически изменена в окне (T,T'], 0 иначе
    # Метка-источник для аудита: какой факт изменения дал label=1
    label_source: str = ""


def _json_default(o: Any) -> Any:
    if isinstance(o, BaseModel):
        return o.model_dump()
    if isinstance(o, set):
        return list(o)
    return str(o)


def dump_jsonl(rows: List[Any], path: str) -> None:
    """Сериализация списка записей в JSONL (одна JSON-строка на строку)."""
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, default=_json_default) + "\n")


def canonicalize_predicate(text: Any) -> str:
    """Нормализация предиката изменения нормы через словарь синонимов."""
    if isinstance(text, (bytes, bytearray)):
        s = text.decode("utf-8", errors="replace")
    else:
        s = str(text or "")
    s = " ".join(s.strip().lower().split())
    if not s:
        return ""
    s = s.replace("-", " ").replace("_", " ")
    s = s.replace(" ", "_")
    return AMENDMENT_ALIASES.get(s, s)


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out
