# SPDX-License-Identifier: GPL-3.0-or-later
"""Клиент официального интернет-портала правовой информации (stdlib-only).

Официальный портал опубликования НПА РФ. Модуль формирует карточки актов и
прямые ссылки на официальные тексты по известным идентификаторам.

Правовое основание: п. 6 ст. 1259 ГК РФ — официальные документы государственных
органов не являются объектами авторского права.

Жёсткие границы:
  * модуль НЕ обходит капчу/paywall и НЕ краулит по произвольным ссылкам;
  * используются только официальные идентификаторы документов;
  * загрузка тел актов — только через общий ``download`` (https + allow-list).
"""

from __future__ import annotations

from typing import Any

SERVICE = "pravo_gov_ru"
BASE_URL = "https://pravo.gov.ru"
# Официальный портал — официальный документ, свободный от авторского права.
LICENSE = "official-document"
COPYRIGHT_STATUS = "public-domain"


def document_url(doc_id: str) -> str:
    """Официальный URL карточки акта на портале (по идентификатору публикации)."""
    return f"{BASE_URL}/proxy/ips/?docbody=&nd={doc_id}"


def normalize_act(
    *,
    doc_id: str,
    title: str,
    year: int | None,
    doc_type: str = "npa",
    abstract: str | None = None,
    oa_url: str | None = None,
) -> dict[str, Any]:
    """Собрать каноническую запись кандидата по официальному акту.

    Ничего не выдумывает: если ``abstract`` нет — остаётся ``None``.
    """
    return {
        "service": SERVICE,
        "service_id": doc_id,
        "title": title,
        "abstract": abstract,
        "abstract_ru": None,
        "year": year,
        "language": "ru",
        "oa_url": oa_url or document_url(doc_id),
        "landing_url": document_url(doc_id),
        "license": LICENSE,
        "source_url": document_url(doc_id),
        "copyright_status": COPYRIGHT_STATUS,
        "source_type": doc_type,
        "is_oa": True,
        "domain": "NPA_RF",
        "provenance_service": "pravo.gov.ru",
    }
