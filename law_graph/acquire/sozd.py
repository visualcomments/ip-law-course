# SPDX-License-Identifier: GPL-3.0-or-later
"""Клиент API Системы обеспечения законодательной деятельности (СОЗД, stdlib).

Официальный API Государственной Думы РФ: карточки законопроектов по внесению
изменений в Гражданский кодекс РФ и сопутствующие материалы (пояснительные
записки, этапы прохождения).

API: ``https://sozd.duma.gov.ru/api`` — POST/GET JSON.

Правовое основание: официальные документы органов власти — не объекты
авторского права (п. 6 ст. 1259 ГК РФ).

Границы: только официальный API; никакого парсинга сторонних сайтов; токен
(если требуется) — только из переменной окружения, не логируется.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

SERVICE = "sozd_duma"
BASE_URL = "https://sozd.duma.gov.ru/api"
LICENSE = "official-document"
COPYRIGHT_STATUS = "public-domain"

USER_AGENT = "ip-law-acquire/1.0 (+https://github.com/visualcomments; educational)"


def _token() -> str | None:
    value = os.environ.get("SOZD_API_TOKEN", "").strip()
    return value or None


def get_json(
    path: str, *, params: dict[str, Any] | None = None, timeout: float = 30.0
) -> Any:
    """GET JSON с официального API СОЗД (токен — только из окружения)."""
    import urllib.parse

    url = f"{BASE_URL}/{path.lstrip('/')}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    token = _token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} для {BASE_URL}/{path}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"сетевая ошибка для {BASE_URL}/{path}: {exc.reason}"
        ) from None


def normalize_bill(bill: dict[str, Any]) -> dict[str, Any]:
    """Преобразовать карточку законопроекта СОЗД в канонического кандидата."""
    identifier = str(bill.get("id") or bill.get("sozdId") or "")
    return {
        "service": SERVICE,
        "service_id": identifier,
        "title": bill.get("name") or bill.get("title"),
        "abstract": bill.get("annotation") or bill.get("note"),
        "abstract_ru": None,
        "year": _as_year(bill.get("date") or bill.get("registrationDate")),
        "language": "ru",
        "oa_url": f"{BASE_URL}/bills/{identifier}" if identifier else None,
        "landing_url": f"https://sozd.duma.gov.ru/bill/{identifier}"
        if identifier
        else None,
        "license": LICENSE,
        "source_url": f"https://sozd.duma.gov.ru/bill/{identifier}"
        if identifier
        else None,
        "copyright_status": COPYRIGHT_STATUS,
        "source_type": "npa",
        "is_oa": True,
        "domain": "NPA_RF",
        "provenance_service": "sozd.duma.gov.ru",
    }


def _as_year(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value[:4].isdigit():
        try:
            return int(value[:4])
        except ValueError:
            return None
    return None
