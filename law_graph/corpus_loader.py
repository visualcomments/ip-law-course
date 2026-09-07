# SPDX-FileCopyrightText: 2026 visualcomments ip-law-course contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Загрузка корпуса курса на уровне норм права.

Корпус курса (см. CORPUS.md) лежит в каталоге COURSE_CORPUS_ROOT/txt/ и состоит
из официальных текстов российского законодательства (ГК РФ ч. IV, УК РФ и др.),
международных договоров, статей Wikipedia и судебной практики. Все они —
либо официальные документы (не являются объектами авторского права), либо
тексты под свободными лицензиями, поэтому их можно свободно обрабатывать.

Модуль умеет:
- перечислять доступные файлы корпуса (txt/*.txt) и их источники;
- загружать текст файла, деля его на «норм-чанки» (статья / пункт / часть);
- предоставлять «синтетический корпус поправок» для автономного (офлайн)
  запуска демонстрации без внешних данных — по аналогии с офлайн-режимом
  проекта top-papers-graph.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))


@dataclass
class NormChunk:
    """Фрагмент корпуса, соответствующий одной норме права."""

    source_doc: str  # имя файла корпуса, напр. txt/gk_rf_part4.txt
    source_law: str  # напр. «ГК РФ»
    article: str     # напр. «ст.1229»
    clause: str      # напр. «п.1» (может быть пустым)
    text: str        # текст нормы (чанк)
    chunk_id: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)


_LAW_ALIASES = {
    "гк рф": "ГК РФ",
    "гк_рф": "ГК РФ",
    "gk rf": "ГК РФ",
    "gk_rf": "ГК РФ",
    "гражданский кодекс": "ГК РФ",
    "гражданский кодекс рф": "ГК РФ",
    "част 4": "ГК РФ",
    "гк": "ГК РФ",
    "ук рф": "УК РФ",
    "ук_рф": "УК РФ",
    "uk rf": "УК РФ",
    "uk_rf": "УК РФ",
    "уголовный кодекс": "УК РФ",
    "коАП": "КоАП РФ",
    "koap": "КоАП РФ",
    "арбитражный процессуальный": "АПК РФ",
    "apk": "АПК РФ",
}


def normalize_law(name: str) -> str:
    n = " ".join((name or "").lower().replace("_", " ").split())
    for key, val in _LAW_ALIASES.items():
        if key in n:
            return val
    return name.strip()


def list_corpus_files(root: Optional[str] = None) -> List[str]:
    """Список файлов корпуса txt/*.txt относительно COURSE_CORPUS_ROOT."""
    if root is None:
        root = os.environ.get("COURSE_CORPUS_ROOT", "")
    if not root:
        return []
    txt_dir = os.path.join(root, "txt")
    if not os.path.isdir(txt_dir):
        return []
    return sorted(os.path.join(txt_dir, f) for f in os.listdir(txt_dir) if f.endswith(".txt"))


def _split_into_norm_chunks(text: str, source_doc: str) -> List[Dict[str, str]]:
    """Делит текст закона на чанки по статьям/пунктам.

    Заголовки статей вида «Статья 1229», «Статья 1270. Использование...»,
    «п. 1», «2.1)» выступают границами. Возвращает список {article, clause, text}.
    """
    chunks: List[Dict[str, str]] = []
    lines = (text or "").splitlines()
    current_article = ""
    current_clause = ""
    buf: List[str] = []
    article_re = re.compile(r"^\s*[Сс]татья\s+([0-9]+[а-яА-Я]?(?:\.[0-9]+)?)", re.I)
    clause_re = re.compile(r"^\s*(?:п(?:ункт)?\.?|часть|ч\.)\s*([0-9]+)", re.I)

    def flush():
        nonlocal buf, current_article, current_clause
        chunk_text = "\n".join(buf).strip()
        if chunk_text and current_article:
            chunks.append(
                {"article": current_article, "clause": current_clause.strip(), "text": chunk_text}
            )
        buf = []

    for line in lines:
        a = article_re.match(line)
        if a:
            flush()
            current_article = f"ст.{a.group(1)}"
            current_clause = ""
            buf = [line]
            continue
        c = clause_re.match(line)
        if c and (len(line) < 80):  # короткая строка-заголовок пункта
            if current_article:
                flush()
            current_clause = f"п.{c.group(1)}"
            buf = [line]
            continue
        buf.append(line)
    flush()
    return chunks


def load_law_file(path: str, source_law: Optional[str] = None) -> List[NormChunk]:
    """Загружает один текстовый файл корпуса и разбивает его на норм-чанки."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    law = source_law or normalize_law(os.path.basename(path))
    base = os.path.basename(path)
    chunks: List[NormChunk] = []
    for i, c in enumerate(_split_into_norm_chunks(text, base)):
        norm_text = c["text"][:600]
        chunks.append(
            NormChunk(
                source_doc=base,
                source_law=law,
                article=c["article"],
                clause=c["clause"],
                text=c["text"],
                chunk_id=f"{base}#{i + 1}",
                meta={"article": c["article"], "clause": c["clause"]},
            )
        )
    return chunks


# ---------------------------------------------------------------------------
# Синтетический корпус поправок для офлайн-демо
# ---------------------------------------------------------------------------

# Примерная динамика изменения норм ГК РФ ч. IV и УК РФ по годам. Поля:
# (закон, статья, тип_изменения, год, документ_поправки, краткое_содержание)
SYNTHETIC_AMENDMENTS: List[Dict[str, str]] = [
    # ГК РФ ч. IV — авторское право
    {"law": "ГК РФ", "article": "ст.1225", "clause": "", "pred": "введена",
     "year": "2008", "src": "ФЗ-230 от 18.12.2006 (часть 4 ГК РФ)",
     "note": "Охраняемые результаты интеллектуальной деятельности"},
    {"law": "ГК РФ", "article": "ст.1229", "clause": "", "pred": "изложена_в_новой_редакции",
     "year": "2014", "src": "ФЗ-35 от 12.03.2014",
     "note": "Распоряжение исключительным правом; свободная лицензия"},
    {"law": "ГК РФ", "article": "ст.1270", "clause": "", "pred": "дополнена",
     "year": "2011", "src": "ФЗ-336 от 28.11.2011 (о «глобальной лицензии» в ред. проекта)",
     "note": "Использование произведения; доведение до всеобщего сведения"},
    {"law": "ГК РФ", "article": "ст.1270", "clause": "", "pred": "дополнена",
     "year": "2014", "src": "ФЗ-35 от 12.03.2014",
     "note": "Свободные лицензии; использование на условиях открытой лицензии"},
    {"law": "ГК РФ", "article": "ст.1272", "clause": "", "pred": "изменена",
     "year": "2014", "src": "ФЗ-35 от 12.03.2014",
     "note": "Исчерпание прав; распространение оригинала и экземпляров"},
    {"law": "ГК РФ", "article": "ст.1252", "clause": "", "pred": "дополнена",
     "year": "2014", "src": "ФЗ-364 от 13.07.2015",
     "note": "Защита исключительных прав; блокировка сайтов-нарушителей"},
    {"law": "ГК РФ", "article": "ст.1301", "clause": "", "pred": "изменена",
     "year": "2014", "src": "ФЗ-35 от 12.03.2014",
     "note": "Компенсация за нарушение; размеры"},
    {"law": "ГК РФ", "article": "ст.1286", "clause": "", "pred": "дополнена",
     "year": "2014", "src": "ФЗ-35 от 12.03.2014",
     "note": "Открытая лицензия на использование произведения"},
    {"law": "ГК РФ", "article": "ст.1299", "clause": "", "pred": "дополнена",
     "year": "2015", "src": "ФЗ-187 от 02.07.2013",
     "note": "Технические средства защиты авторских прав"},
    {"law": "ГК РФ", "article": "ст.1263", "clause": "", "pred": "дополнена",
     "year": "2019", "src": "ФЗ-242 от 01.10.2019 (остроумное) «об эфирном вещании»",
     "note": "Аудиовизуальное произведение; режиссёр-постановщик"},
    # УК РФ — ответственность
    {"law": "УК РФ", "article": "ст.146", "clause": "", "pred": "изменена",
     "year": "2003", "src": "ФЗ-162 от 08.12.2003",
     "note": "Нарушение авторских и смежных прав"},
    {"law": "УК РФ", "article": "ст.146", "clause": "", "pred": "дополнена",
     "year": "2014", "src": "ФЗ-530 от 31.12.2014",
     "note": "Плагиат; конфискация оборудования"},
]

# Причинно-следственные связи норм (влияние норм друг на друга)
SYNTHETIC_INFLUENCE: List[Dict[str, str]] = [
    {"from_law": "ГК РФ", "from_article": "ст.1270", "pred": "отсылает_к",
     "to_law": "ГК РФ", "to_article": "ст.1229", "linked": "порядок распоряжения"},
    {"from_law": "ГК РФ", "from_article": "ст.1252", "pred": "отсылает_к",
     "to_law": "ГК РФ", "to_article": "ст.1301", "linked": "меры защиты и компенсация"},
    {"from_law": "ГК РФ", "from_article": "ст.1286", "pred": "влечёт_изменение",
     "to_law": "ГК РФ", "to_article": "ст.1233", "linked": "лицензионный договор"},
]


def load_synthetic_corpus() -> Dict[str, Any]:
    """Возвращает синтетический «корпус поправок» для офлайн-демо.

    Возвращает dict с ключами: amendments (List[Dict]), influence (List[Dict]),
    source="synthetic".
    """
    return {"amendments": SYNTHETIC_AMENDMENTS, "influence": SYNTHETIC_INFLUENCE, "source": "synthetic"}
