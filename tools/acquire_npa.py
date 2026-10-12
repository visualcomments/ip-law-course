#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Массовый сбор НПА для курса «Право интеллектуальной собственности».

Формирует JSONL-манифест кандидатов (официальные акты и карточки
законопроектов) для последующей пакетной обработки агентом с юридическим
харнессом. Байты тел актов скачиваются ЛОКАЛЬНО и вне git.

Usage:
  python tools/acquire_npa.py topics
  python tools/acquire_npa.py manifest --out .local/legal-bronze/candidates.jsonl \\
      [--acts-json acts.json]
  python tools/acquire_npa.py fetch --manifest .local/legal-bronze/candidates.jsonl \\
      --out-dir .local/legal-bronze

Границы:
  * персональные данные слушателей не собираются и не хранятся никогда;
  * только официальные документы (п. 6 ст. 1259 ГК РФ);
  * байты — только локально, вне git; секреты не логируются.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from law_graph.acquire import pravo  # noqa: E402

# Встроенный каталог тем (правовые блоки ГК РФ ч. IV и специальные законы).
TOPIC_CATALOG = {
    "AUTHOR": [
        "ФЗ-35 от 12.03.2014 (изменения в части первую, вторую и четвертую ГК РФ)",
        "ФЗ-187 от 02.07.2013 (о свободных лицензиях, ст. 1286.1 ГК РФ)",
    ],
    "RELATED": [
        "ФЗ-230 от 18.12.2006 (четвертая часть ГК РФ, вступление в силу)",
        "ФЗ-142 от 18.12.2006 (о смежных правах)",
    ],
    "PATENT": [
        "ГК РФ ч. IV, глава 72 (патентное право, ст. 1345-1407)",
        "ГК РФ ч. IV, ст. 1360 (принудительная лицензия)",
    ],
    "TM": [
        "ФЗ-230 от 26.07.2019 (географические указания и НМПТ)",
        "ГК РФ ч. IV, глава 76 (средства индивидуализации, ст. 1477-1541)",
    ],
}

# Хосты официальных правовых ресурсов, отдающих текст акта напрямую.
ALLOWED_HOSTS = {
    "pravo.gov.ru",
    "sozd.duma.gov.ru",
    "publication.pravo.gov.ru",
    "docs.cntd.ru",
}
DEFAULT_MAX_BYTES = 25 * 1024 * 1024


def _is_allowed(url: str) -> tuple[bool, str]:
    if not url:
        return False, "URL отсутствует"
    parts = urlsplit(url)
    if parts.scheme != "https":
        return False, f"разрешён только https, получено {parts.scheme!r}"
    host = (parts.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        return False, f"хост {host!r} не входит в allow-list правовых ресурсов"
    return True, ""


def cmd_topics(_args: argparse.Namespace) -> int:
    print(json.dumps(TOPIC_CATALOG, ensure_ascii=False, indent=2))
    return 0


def _load_acts(path: str | None) -> list[dict]:
    """Прочитать входной список актов (JSON-массив карточек) или вернуть []."""
    if not path:
        return []
    # utf-8-sig устойчив к BOM (частый случай при правках в Windows-редакторах).
    with open(path, encoding="utf-8-sig") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("ожидается JSON-массив записей об актах")
    return data


def cmd_manifest(args: argparse.Namespace) -> int:
    acts = _load_acts(args.acts_json)
    rows: list[dict] = []
    for act in acts:
        rows.append(
            pravo.normalize_act(
                doc_id=str(act.get("doc_id") or ""),
                title=str(act.get("title") or ""),
                year=act.get("year"),
                doc_type=act.get("doc_type", "npa"),
                abstract=act.get("abstract"),
                oa_url=act.get("oa_url"),
            )
        )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {"command": "manifest", "records": len(rows), "out": str(out)},
            ensure_ascii=False,
        )
    )
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        print(
            json.dumps(
                {"error": f"манифест не найден: {manifest_path}"}, ensure_ascii=False
            ),
            file=sys.stderr,
        )
        return 2
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    skipped = 0
    outcomes: list[dict] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        url = str(row.get("oa_url") or "")
        ok, why = _is_allowed(url)
        if not ok:
            skipped += 1
            outcomes.append(
                {
                    "service_id": row.get("service_id"),
                    "status": "skipped",
                    "reason": why,
                }
            )
            continue
        try:
            req = urllib.request.Request(  # noqa: S310
                url,
                headers={
                    "User-Agent": "ip-law-acquire/1.0 (+https://github.com/visualcomments)"
                },
            )
            with urllib.request.urlopen(req, timeout=args.timeout) as resp:  # noqa: S310
                body = resp.read(DEFAULT_MAX_BYTES + 1)
        except Exception as exc:  # noqa: BLE001
            skipped += 1
            outcomes.append(
                {
                    "service_id": row.get("service_id"),
                    "status": "skipped",
                    "reason": str(exc),
                }
            )
            print(
                f"  skipped {row.get('service_id')}: {str(exc)[:80]}",
                file=sys.stderr,
            )
            continue
        sha = hashlib.sha256(body).hexdigest()
        target = out_dir / f"{row.get('service_id') or 'act'}.txt"
        target.write_bytes(body)
        downloaded += 1
        outcomes.append(
            {
                "service_id": row.get("service_id"),
                "status": "downloaded",
                "path": str(target),
                "sha256": sha,
                "bytes": len(body),
            }
        )

    fetch_manifest = out_dir / "fetch-manifest.jsonl"
    with open(fetch_manifest, "w", encoding="utf-8", newline="\n") as fh:
        for outcome in outcomes:
            fh.write(json.dumps(outcome, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "command": "fetch",
                "downloaded": downloaded,
                "skipped": skipped,
                "out_dir": str(out_dir),
                "fetch_manifest": str(fetch_manifest),
            },
            ensure_ascii=False,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Массовый сбор НПА по официальным источникам."
    )
    sub = ap.add_subparsers(dest="command", required=True)

    pt = sub.add_parser("topics", help="Каталог правовых тем/блоков.")
    pt.set_defaults(func=cmd_topics)

    pm = sub.add_parser("manifest", help="Собрать JSONL-манифест из списка актов.")
    pm.add_argument("--acts-json", default="", help="JSON-массив карточек актов.")
    pm.add_argument(
        "--out",
        default=".local/legal-bronze/candidates.jsonl",
        help="Путь к JSONL-манифесту.",
    )
    pm.set_defaults(func=cmd_manifest)

    pf = sub.add_parser("fetch", help="Загрузить тела актов ЛОКАЛЬНО (вне git).")
    pf.add_argument("--manifest", required=True)
    pf.add_argument("--out-dir", default=".local/legal-bronze")
    pf.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Таймаут на один акт в секундах (официальные порталы бывают медленными).",
    )
    pf.set_defaults(func=cmd_fetch)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
