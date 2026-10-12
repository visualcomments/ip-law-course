#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Тесты массового сбора НПА (без сети).

Проверяют каталог тем, сборку манифеста из карточек актов, право-гейт
allow-list и то, что персональные данные слушателей не попадают в манифест.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_SPEC = importlib.util.spec_from_file_location(
    "acquire_npa", ROOT / "tools" / "acquire_npa.py"
)
assert _SPEC and _SPEC.loader
acquire_npa = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(acquire_npa)

from law_graph.acquire import pravo, sozd  # noqa: E402


def test_topic_catalog_present() -> None:
    for key in ("AUTHOR", "RELATED", "PATENT", "TM"):
        assert key in acquire_npa.TOPIC_CATALOG
        assert len(acquire_npa.TOPIC_CATALOG[key]) >= 1


def test_allowlist_accepts_official_hosts() -> None:
    ok, _ = acquire_npa._is_allowed("https://pravo.gov.ru/proxy/ips/?docbody=&nd=1")
    assert ok is True
    ok, _ = acquire_npa._is_allowed("https://sozd.duma.gov.ru/bill/1")
    assert ok is True


def test_allowlist_rejects_non_https_and_foreign_hosts() -> None:
    assert acquire_npa._is_allowed("http://pravo.gov.ru/x")[0] is False
    assert acquire_npa._is_allowed("https://evil.example.com/x")[0] is False
    assert acquire_npa._is_allowed("")[0] is False


def test_pravo_act_is_official_document() -> None:
    row = pravo.normalize_act(doc_id="102171587", title="ФЗ-35", year=2014)
    assert row["service"] == "pravo_gov_ru"
    assert row["license"] == "official-document"
    assert row["copyright_status"] == "public-domain"
    assert row["abstract"] is None  # ничего не выдумывается


def test_sozd_bill_normalization() -> None:
    bill = {
        "id": "123456-8",
        "name": "О внесении изменений в ГК РФ",
        "date": "2020-01-15",
    }
    row = sozd.normalize_bill(bill)
    assert row["service"] == "sozd_duma"
    assert row["service_id"] == "123456-8"
    assert row["year"] == 2020
    assert row["license"] == "official-document"


def test_manifest_command_and_no_personal_data(tmp_path: Path, capsys) -> None:
    acts_path = tmp_path / "acts.json"
    acts_path.write_text(
        json.dumps(
            [
                {"doc_id": "1", "title": "ФЗ-1", "year": 2010, "doc_type": "npa"},
                {"doc_id": "2", "title": "ФЗ-2", "year": 2011},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = tmp_path / "candidates.jsonl"
    rc = acquire_npa.main(
        ["manifest", "--acts-json", str(acts_path), "--out", str(out)]
    )
    assert rc == 0
    lines = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2
    # В манифесте — только официальные реквизиты, никаких персональных данных.
    for row in lines:
        assert "email" not in row
        assert "student" not in row
        assert row["license"] == "official-document"


def test_manifest_handles_utf8_bom(tmp_path: Path) -> None:
    acts_path = tmp_path / "acts_bom.json"
    acts_path.write_text(
        json.dumps(
            [{"doc_id": "3", "title": "ФЗ-3", "year": 2012}], ensure_ascii=False
        ),
        encoding="utf-8-sig",
    )
    out = tmp_path / "c.jsonl"
    rc = acquire_npa.main(
        ["manifest", "--acts-json", str(acts_path), "--out", str(out)]
    )
    assert rc == 0
    assert len(out.read_text(encoding="utf-8").splitlines()) == 1
