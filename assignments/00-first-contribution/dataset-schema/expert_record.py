#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""expert_record.py — детерминированный помощник эксперта курса (схема 1).

Эксперт указывает источник и короткую фразу-якорь. Скрипт сам берёт ДОСЛОВНЫЙ
фрагмент источника (окно вокруг якоря), собирает запись схемы и проверяет её
валидатором. Цитата не выдумывается — это гарантия от галлюцинаций агента.

Подкоманды:
  find   --file <путь> --phrase "<фраза>"                найти окна-кандидаты
  add    --kind amendment|experiment --nick <ник> ...    собрать запись и проверить
  check  --out <records.jsonl> [--corpus-root <root>]    проверить файл записей
  status --out <records.jsonl>                           сколько записей уже есть

Примеры:
  python expert_record.py find --file "reading_ru/ru__...txt" --phrase "147-ФЗ" ^
      --corpus-root "C:\\Users\\nonhumanbox\\courses\\ip-law-course"
  python expert_record.py add --kind amendment --nick ivanov --out records-ivanov.jsonl ^
      --file reading_ru/ru__...txt --phrase "147-ФЗ" --source-law "ГК РФ" --article "ст.1252" ^
      --amending-doc "Федеральный закон от 01.07.2017 № 147-ФЗ" --predicate изменена ^
      --ts 2017 --change "Закон изменил статью 1252 ГК РФ." ^
      --corpus-root "C:\\Users\\nonhumanbox\\courses\\ip-law-course"
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

KIT = Path(__file__).resolve().parent
VALIDATE = KIT / "validate.py"
CURRENT_DAY = date.today().isoformat()

PREDICATES = [
    "изменена",
    "дополнена",
    "введена",
    "изложена_в_новой_редакции",
    "признана_утратившей_силу",
    "исключена",
    "уточнена",
]
PRED_ALIASES = {
    "изменение": "изменена",
    "дополнение": "дополнена",
    "добавлена": "введена",
    "новая редакция": "изложена_в_новой_редакции",
    "утратила силу": "признана_утратившей_силу",
}
DEFAULT_ROOTS = {
    "ip-law-course": r"C:\Users\nonhumanbox\courses\ip-law-course",
    "history-of-science-and-technology": r"C:\Users\nonhumanbox\courses\history-of-science-and-technology",
    "oa": r"C:\Users\nonhumanbox\courses\_literature-tools",
}


def norm(s: str) -> str:
    s = s.replace("\u00ad", "").replace("\u2010", "-").replace("\u2011", "-")
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)
    return re.sub(r"\s+", " ", s).strip()


def resolve(file_rel: str, roots: list[Path]) -> Path | None:
    p = Path(file_rel)
    if p.is_absolute() and p.is_file():
        return p
    for r in roots:
        c = r / file_rel
        if c.is_file():
            return c
    return None


def roots_from(args) -> list[Path]:
    out = [Path(r) for r in (args.corpus_root or [])]
    return out or [Path(".")]


def windows(
    text: str, phrase: str, ctx_before: int = 70, width: int = 200
) -> list[str]:
    """Все окна нормализованного текста, содержащие нормализованную фразу."""
    ph = norm(phrase)
    if not ph:
        return []
    res, start = [], 0
    while True:
        i = text.find(ph, start)
        if i < 0:
            break
        s = max(0, i - ctx_before)
        res.append(text[s : s + width].strip())
        start = i + max(1, len(ph))
        if len(res) >= 25:
            break
    return res


def slug(s: str) -> str:
    return re.sub(r"[^a-zа-я0-9]+", "-", (s or "").lower()).strip("-")


def norm_id(source_law: str, article: str, clause: str) -> str:
    law = slug(source_law) or "unknown-law"

    def seg(part: str, prefix: str) -> str:
        p = norm(part).lower()
        if not p:
            return ""
        m = re.search(r"(?:ст\.?|статья|статьи)\s*([0-9]+[а-я]?(?:\.[0-9]+)?)", p)
        if m:
            return f"ст.{m.group(1)}"
        m = re.search(r"(?:п\.?|пункт)\s*([0-9]+)", p)
        if m:
            return f"п.{m.group(1)}"
        m = re.search(r"(?:ч\.?|часть)\s*([0-9]+)", p)
        if m:
            return f"ч.{m.group(1)}"
        m = re.search(r"^([0-9]+[а-я]?(?:\.[0-9]+)?)$", p)
        return f"{prefix}{m.group(1)}" if m else p

    nid = f"{law}/{seg(article, 'ст.')}" if article else law
    if clause:
        nid = f"{nid}/{seg(clause, 'п.')}"
    return nid


def canon_predicate(s: str) -> str:
    key = norm(s).lower().replace("-", "_").replace(" ", "_")
    key = PRED_ALIASES.get(norm(s).lower(), key)
    return key if key in PREDICATES else "изменена"


def existing_count(out: Path) -> int:
    if not out.is_file():
        return 0
    return len([l for l in out.read_text(encoding="utf-8").splitlines() if l.strip()])


def run_validate(out: Path, roots: list[Path]) -> int:
    cmd = [sys.executable, str(VALIDATE), str(out)]
    for r in roots:
        cmd += ["--corpus-root", str(r)]
    print("\n--- проверка (validate.py) ---")
    proc = subprocess.run(cmd, text=True, encoding="utf-8", capture_output=True)
    print(proc.stdout.strip() or proc.stderr.strip())
    return proc.returncode


def cmd_find(args) -> int:
    roots = roots_from(args)
    src = resolve(args.file, roots)
    if src is None:
        print(f"НЕ НАЙДЕН файл: {args.file} (проверены: {[str(r) for r in roots]})")
        return 2
    text = norm(src.read_text(encoding="utf-8", errors="replace"))
    wins = windows(text, args.phrase)
    if not wins:
        print(f"Фраза не найдена: {args.phrase!r}. Попробуйте короче или другое слово.")
        return 1
    print(f"Найдено окон: {len(wins)} (файл: {src})")
    for i, w in enumerate(wins, 1):
        print(f"\n[{i}] …{w}…")
    print("\nДля записи возьмите одну из фраз выше как --phrase (любой её фрагмент).")
    return 0


def parse_figures(items) -> list[dict]:
    """Формат элемента: 'path|kind|caption|rights' (kind/caption/rights опциональны)."""
    out: list[dict] = []
    for it in items or []:
        parts = [p.strip() for p in str(it).split("|")]
        path = parts[0] if parts else ""
        if not path:
            continue
        kind = parts[1] if len(parts) > 1 and parts[1] else "chart"
        caption = parts[2] if len(parts) > 2 and parts[2] else None
        rights = parts[3] if len(parts) > 3 and parts[3] else "own"
        out.append(
            {
                "path": path,
                "kind": kind,
                "caption_ru": caption,
                "rights": rights,
                "redrawn": rights == "own",
            }
        )
    return out


def build_amendment(args, quote: str) -> dict:
    return {
        "schema": 1,
        "record_id": args.record_id
        or f"{args.nick}-amd-{existing_count(Path(args.out)) + 1}",
        "profile": "amendment",
        "title_ru": args.title or args.change[:120],
        "norm": {
            "source_law": args.source_law,
            "article": args.article,
            "clause": args.clause or None,
            "norm_id": norm_id(args.source_law, args.article, args.clause or ""),
        },
        "amending_doc": args.amending_doc,
        "predicate": canon_predicate(args.predicate),
        "ts": args.ts or None,
        "granularity": args.granularity
        or (
            "year"
            if not args.ts
            else "day"
            if re.match(r"^\d{4}-\d{2}-\d{2}$", args.ts)
            else "month"
            if re.match(r"^\d{4}-\d{2}$", args.ts)
            else "year"
        ),
        "change_ru": args.change,
        "figures": parse_figures(args.figure),
        "before_ru": None,
        "after_ru": None,
        "source": {
            "file": args.file,
            "coord": args.coord or "файл · фрагмент (уточнить)",
            "doc_type": args.doc_type,
            "license": args.license,
            "url": None,
        },
        "provenance": {
            "extracted_by": args.nick,
            "extracted_at": CURRENT_DAY,
            "method": "assisted",
            "derivation": args.derivation,
            "tool": "opencode expert-helper",
        },
        "review": {
            "status": "proposed",
            "note_ru": "источник обработан; требуется проверка эксперта",
        },
        "confidence": 0.6,
        "evidence_quote": quote,
    }


def build_experiment(args, quote: str) -> dict:
    return {
        "schema": 1,
        "record_id": args.record_id
        or f"{args.nick}-exp-{existing_count(Path(args.out)) + 1}",
        "profile": "experiment",
        "title_ru": args.title or args.subject[:120],
        "domain": args.domain or "other",
        "study": {
            "authors": args.authors or None,
            "year": args.year or None,
            "journal": args.journal or None,
            "language": args.language or "en",
        },
        "experiment": {
            "subject_ru": args.subject,
            "method_ru": args.method,
            "conditions_ru": args.conditions or None,
            "apparatus": args.apparatus or None,
        },
        "measurements": [
            {
                "variable_ru": args.variable,
                "value": args.value,
                "unit": args.unit,
                "condition_ru": args.conditions or None,
                "quality": args.quality or "ocr_uncertain",
            }
        ],
        "figures": parse_figures(args.figure),
        "outcome_ru": args.outcome,
        "source": {
            "file": args.file,
            "coord": args.coord or "файл · фрагмент (уточнить)",
            "doc_type": args.doc_type,
            "license": args.license,
            "url": None,
        },
        "provenance": {
            "extracted_by": args.nick,
            "extracted_at": CURRENT_DAY,
            "method": "assisted",
            "derivation": args.derivation,
            "tool": "opencode expert-helper",
        },
        "review": {
            "status": "proposed",
            "note_ru": "источник обработан; требуется проверка эксперта",
        },
        "confidence": 0.6,
        "evidence_quote": quote,
    }


def cmd_add(args) -> int:
    roots = roots_from(args)
    facts = args.derivation == "facts_reworked"
    quote = ""
    if facts:
        if not norm(args.coord or ""):
            print(
                "Для facts_reworked обязателен --coord (координата источника: страница/раздел)."
            )
            return 2
    else:
        src = resolve(args.file, roots)
        if src is None:
            print(
                f"НЕ НАЙДЕН файл: {args.file}. Подсказка: запустите `find` или проверьте --corpus-root."
            )
            return 2
        if not norm(args.phrase):
            print("Укажите --phrase (фразу-якорь) или --derivation facts_reworked.")
            return 2
        text = norm(src.read_text(encoding="utf-8", errors="replace"))
        wins = windows(text, args.phrase)
        if not wins:
            print(
                f"Фраза-якорь не найдена: {args.phrase!r}. Возьмите фразу из файла дословно (`find`)."
            )
            return 1
        quote = wins[args.pick - 1] if 1 <= args.pick <= len(wins) else wins[0]

    if args.kind == "amendment":
        missing = [
            f
            for f, v in [
                ("--source-law", args.source_law),
                ("--article", args.article),
                ("--amending-doc", args.amending_doc),
                ("--predicate", args.predicate),
                ("--change", args.change),
            ]
            if not v
        ]
        if missing:
            print("Для amendment обязательны: " + ", ".join(missing))
            return 2
        rec = build_amendment(args, quote)
    else:
        missing = [
            f
            for f, v in [
                ("--subject", args.subject),
                ("--method", args.method),
                ("--variable", args.variable),
                ("--value", args.value),
                ("--outcome", args.outcome),
            ]
            if not v
        ]
        if missing:
            print("Для experiment обязательны: " + ", ".join(missing))
            return 2
        rec = build_experiment(args, quote)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    total = existing_count(out)
    print(f"Добавлена запись #{total}: {rec['record_id']}  (профиль {rec['profile']})")
    print(f"Цитата: …{quote[:160]}…")
    print(f"Файл записей: {out.resolve()}  —  строк: {total}")

    rc = run_validate(out, roots)
    if total < 3:
        print(f"\nНужно ещё записей: {3 - total} (базовое задание — 3 записи).")
    else:
        print(
            "\n3+ записи есть — базовое задание по данным выполнено. Осталось сдать файл."
        )
    return 0 if rc == 0 else rc


def cmd_check(args) -> int:
    out = Path(args.out)
    if not out.is_file():
        print(f"Нет файла записей: {out}")
        return 2
    return run_validate(out, roots_from(args))


def cmd_status(args) -> int:
    out = Path(args.out)
    n = existing_count(out)
    print(
        f"{out.resolve()} — записей: {n}"
        + ("  (базовое задание: 3)" if n < 3 else "  ✔")
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Помощник эксперта курса (схема 1)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--corpus-root", action="append", default=[])
        p.add_argument("--file", required=True)

    f = sub.add_parser("find")
    common(f)
    f.add_argument("--phrase", required=True)
    f.set_defaults(func=cmd_find)

    a = sub.add_parser("add")
    common(a)
    a.add_argument("--kind", required=True, choices=["amendment", "experiment"])
    a.add_argument("--out", required=True)
    a.add_argument("--nick", required=True)
    a.add_argument("--pick", type=int, default=1)
    a.add_argument("--record-id")
    a.add_argument("--title")
    a.add_argument("--coord")
    a.add_argument("--doc-type", default="scientific_article")
    a.add_argument("--license", default="cite-only")
    a.add_argument(
        "--derivation",
        default="verbatim_quote",
        choices=["verbatim_quote", "facts_reworked"],
        help="facts_reworked — факт изложен своими словами (без дословной цитаты); нужен --coord",
    )
    a.add_argument(
        "--phrase",
        default="",
        help="фраза-якорь для дословной цитаты (не нужна при --derivation facts_reworked)",
    )
    a.add_argument(
        "--figure",
        action="append",
        default=[],
        help="изображение: 'path|kind|caption|rights' (права: own/PD/CC0/CC-BY-4.0/CC-BY-SA-4.0/official-document/permission)",
    )
    # amendment
    a.add_argument("--source-law")
    a.add_argument("--article")
    a.add_argument("--clause")
    a.add_argument("--amending-doc")
    a.add_argument("--predicate")
    a.add_argument("--ts")
    a.add_argument("--granularity")
    a.add_argument("--change")
    # experiment
    a.add_argument("--subject")
    a.add_argument("--method")
    a.add_argument("--conditions")
    a.add_argument("--apparatus")
    a.add_argument("--variable")
    a.add_argument("--value")
    a.add_argument("--unit")
    a.add_argument("--outcome")
    a.add_argument("--domain")
    a.add_argument("--quality")
    a.add_argument("--authors")
    a.add_argument("--year")
    a.add_argument("--journal")
    a.add_argument("--language")
    a.set_defaults(func=cmd_add)

    c = sub.add_parser("check")
    c.add_argument("--out", required=True)
    c.add_argument("--corpus-root", action="append", default=[])
    c.set_defaults(func=cmd_check)

    s = sub.add_parser("status")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_status)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
