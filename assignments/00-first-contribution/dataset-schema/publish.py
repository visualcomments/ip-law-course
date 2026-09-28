#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Сборка и публикация датасета результатов экспертов.

Порядок:
  1) проверить каждый submission (`validate.py`); ошибки структуры/цитаты — стоп;
  2) объединить записи, убрать дубликаты по `record_id`;
  3) отфильтровать по лицензии: публикуем только PD / CC0 / CC-BY-4.0 /
     CC-BY-SA-4.0 / official-document (cite-only и unknown — не публикуем);
  4) записать `records.jsonl` и карточку датасета `README.md` в --out-dir;
  5) если задан --repo-id и есть токен (env HF_TOKEN), загрузить в HuggingFace.

Примеры:
  python publish.py --submissions-dir ../submissions --out-dir ../../dataset --dry-run
  HF_TOKEN=... python publish.py --submissions-dir ../submissions \\
      --out-dir ../../dataset --repo-id chaotic-good-project/ip-law-expert-records
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
VALIDATE = HERE / "validate.py"

PUBLISHABLE = {
    "PD",
    "CC0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "official-document",
    "facts-derived",
}
# Изображения: публикуем только «свои» (перерисованные), свободные или разрешённые.
FIGURE_PUBLISHABLE = {
    "own",
    "PD",
    "CC0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "official-document",
    "permission",
}


def record_publishable(rec: dict, assets_root=None) -> bool:
    """Публикуемо ли: лицензия источника, права на изображения и наличие их файлов."""
    if (rec.get("source") or {}).get("license") not in PUBLISHABLE:
        return False
    for f in rec.get("figures") or []:
        fi = f or {}
        if fi.get("rights") not in FIGURE_PUBLISHABLE:
            return False
        if assets_root is not None:
            p = Path(assets_root) / str(fi.get("path") or "")
            if not p.is_file():
                return False
    return True


def copy_assets(records: list[dict], assets_root: Path, out_dir: Path) -> int:
    """Копирует файлы изображений опубликованных записей в out_dir (для загрузки на HF)."""
    copied = 0
    for rec in records:
        for f in rec.get("figures") or []:
            rel = str((f or {}).get("path") or "")
            src = assets_root / rel
            if not rel or not src.is_file():
                continue
            dst = out_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
            copied += 1
    return copied


def validate_file(path: Path) -> tuple[bool, str]:
    """True, если структура верна (код 0 или 2); False при ошибках (код 1)."""
    proc = subprocess.run(
        [sys.executable, str(VALIDATE), str(path)],
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    out = (proc.stdout or proc.stderr).strip()
    return proc.returncode != 1, out


def load_existing(repo_id: str, token: str) -> dict[str, dict]:
    """Уже опубликованные записи из датасета (чтобы публикация была дополняющей)."""
    try:
        from huggingface_hub import hf_hub_download

        p = hf_hub_download(
            repo_id=repo_id, filename="records.jsonl", repo_type="dataset", token=token
        )
        out: dict[str, dict] = {}
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                r = json.loads(line)
                out[r["record_id"]] = r
        return out
    except Exception as e:  # noqa: BLE001
        print(f"(существующий records.jsonl не прочитан: {e})")
        return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--submissions-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--repo-id", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--title", default="Expert records of the course")
    ap.add_argument(
        "--assets-root",
        default="",
        help="корень, относительно которого лежат пути изображений (по умолчанию — корень репозитория)",
    )
    args = ap.parse_args()

    subs_dir = Path(args.submissions_dir).resolve()
    assets_root = (
        Path(args.assets_root).resolve() if args.assets_root else subs_dir.parents[2]
    )
    subs = sorted(subs_dir.glob("*.jsonl"))
    if not subs:
        print("Нет submissions (*.jsonl) — нечего публиковать.")
        return 0

    records: dict[str, dict] = {}
    failed = 0
    for f in subs:
        ok, out = validate_file(f)
        status = "OK" if ok else "FAIL"
        print(f"[{status}] {f.name}: {out.splitlines()[0] if out else ''}")
        if not ok:
            failed += 1
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            records.setdefault(rec["record_id"], rec)

    if failed:
        print(f"\nСТОП: {failed} файл(ов) не прошли проверку — публикация отменена.")
        return 1

    # Дополняющая публикация: подмешиваем уже опубликованные записи (сдачи приоритетнее).
    if args.repo_id and not args.dry_run:
        token0 = os.environ.get("HF_TOKEN", "")
        if token0:
            existing = load_existing(args.repo_id, token0)
            for rid, rec in existing.items():
                records.setdefault(rid, rec)
            print(
                f"Существующих записей в датасете: {len(existing)}; всего после объединения: {len(records)}"
            )

    published = [r for r in records.values() if record_publishable(r, assets_root)]
    excluded = [r for r in records.values() if not record_publishable(r, assets_root)]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(json.dumps(r, ensure_ascii=False) for r in published)
    (out_dir / "records.jsonl").write_text(
        rows + ("\n" if rows else ""), encoding="utf-8"
    )
    copied = copy_assets(published, assets_root, out_dir)
    if copied:
        print(f"Скопировано изображений: {copied} (в {out_dir})")

    by_profile: dict[str, int] = {}
    for r in published:
        by_profile[r["profile"]] = by_profile.get(r["profile"], 0) + 1

    card = f"""---
license: cc-by-sa-4.0
language:
  - ru
  - en
task_categories:
  - text-classification
  - other
tags:
  - open-education
  - course-dataset
  - expert-annotated
pretty_name: {args.title}
---

# {args.title}

Набор данных, собранный участниками курса в рамках первого задания (роль «эксперт»).
Записи проходят проверку схемой и дословностью цитаты
(`dataset-schema/validate.py`) до попадания сюда. Первичное наполнение —
курированные примеры курса; далее набор пополняется сдачами участников.

- Обновлён: {date.today().isoformat()}
- Записей опубликовано: **{len(published)}** ({", ".join(f"{k}: {v}" for k, v in sorted(by_profile.items())) or "—"})
- Отфильтровано по лицензии (не публикуется): **{len(excluded)}** (cite-only / unknown)

## Поля
Единая схема `universal-record.schema.json`, два профиля: `amendment`
(изменения в статьи НПА) и `experiment` (количественные результаты).
`evidence_quote` — дословный фрагмент источника; `review.status` — статус
содержательной проверки.

### Мультимодальность
Записи могут содержать `figures[]` — изображения (фото/диаграммы/графики/
таблицы) с полем `rights`. Публикуются только изображения с правами
`own`/`PD`/`CC0`/`CC-BY-4.0`/`CC-BY-SA-4.0`/`official-document`/`permission`;
`own` означает, что график **перерисован экспертом** из числовых данных
источника.

### Факты из источников (facts-derived)
Записи вида `source.license="facts-derived"` (`provenance.derivation="facts_reworked"`)
содержат **факты, переработанные и изложенные своими словами** (факты и сообщения
о фактах не охраняются авторским правом — ст. 1259 п. 5 ГК РФ). Для таких записей
`evidence_quote` пуст: дословный фрагмент охраняемого текста не приводится, но
`source.coord` обязателен как якорь провенанса.

## Лицензия и происхождение
Публикуются только записи из источников с публикуемой лицензией
(PD / CC0 / CC-BY-4.0 / CC-BY-SA-4.0 / official-document). Записи из
материалов «только цитирование» (cite-only) исключены. Каждая запись хранит
`source.file` и координату для проверки.

## Как пополнить
См. `assignments/00-first-contribution/README.md` в репозитории курса.
"""
    (out_dir / "README.md").write_text(card, encoding="utf-8")

    print(
        f"\nОпубликовано записей: {len(published)} {by_profile}; отфильтровано: {len(excluded)}"
    )
    print(f"Записано: {out_dir / 'records.jsonl'}, {out_dir / 'README.md'}")

    if args.repo_id and not args.dry_run:
        token = os.environ.get("HF_TOKEN", "")
        if not token:
            print("Нет HF_TOKEN — загрузка пропущена.")
            return 0
        try:
            from huggingface_hub import HfApi
        except ImportError:
            print("huggingface_hub не установлен (pip install huggingface_hub).")
            return 1
        api = HfApi()
        api.create_repo(repo_id=args.repo_id, repo_type="dataset", exist_ok=True)
        api.upload_folder(
            repo_id=args.repo_id, repo_type="dataset", folder_path=str(out_dir)
        )
        print(f"Загружено в https://huggingface.co/datasets/{args.repo_id}")
    elif args.dry_run:
        print("dry-run: загрузка пропущена.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
