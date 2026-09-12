#!/usr/bin/env python3
"""Проверка целостности курса «Право интеллектуальной собственности».

Курс состоит из 16 занятий, программы, корпуса и инструментов. Этот
скрипт следит за тем, чтобы связи между ними не распадались: каждое
занятие существует и достижимо из программы, каждая ссылка разрешается,
структура занятий единообразна.

Запуск:
    python3 tools/validate_course.py [--json]

Код возврата 1 при любой проблеме — чтобы CI падал заметно, а не
пропускал молчаливое расхождение.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LECTURES = ROOT / "lectures"
SYLLABUS_MD = ROOT / "syllabus.md"
SYLLABUS_JSON = ROOT / "syllabus.json"

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
LESSONS = 16

# Every lecture must keep these sections. They encode the pedagogy of the
# course: a claim, its evidence from the corpus, the author's synthesis,
# a way for the student to check themselves, and work to do.
REQUIRED_SECTIONS = (
    "## Цели занятия",
    "## Тезис",
    "## Источники и свидетельства",
    "## Вопросы для самопроверки",
    "## Задания",
)

problems: list[str] = []
checks_run = 0


def check(name: str, condition: bool, message: str) -> None:
    global checks_run
    checks_run += 1
    if not condition:
        problems.append(f"{name}: {message}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="машиночитаемый вывод")
    args = parser.parse_args()

    # ── 1. программа существует и ссылается на занятия ────────────────────
    check("syllabus.md существует", SYLLABUS_MD.is_file(), "файл отсутствует")
    check("syllabus.json существует", SYLLABUS_JSON.is_file(), "файл отсутствует")

    syllabus_text = SYLLABUS_MD.read_text(encoding="utf-8") if SYLLABUS_MD.is_file() else ""
    syllabus_data: dict = {}
    if SYLLABUS_JSON.is_file():
        try:
            syllabus_data = json.loads(SYLLABUS_JSON.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            problems.append(f"syllabus.json не является корректным JSON: {e}")

    # ── 2. каждое занятие существует и достижимо из программы ─────────────
    lecture_files: list[Path] = []
    for n in range(1, LESSONS + 1):
        matches = sorted(LECTURES.glob(f"{n:02d}_*.md"))
        check(f"занятие {n:02d} существует", len(matches) == 1,
              f"найдено файлов: {len(matches)}")
        if not matches:
            continue
        lecture_files.append(matches[0])
        check(f"занятие {n:02d} связано с программой",
              matches[0].name in syllabus_text,
              f"{matches[0].name} не упоминается в syllabus.md")

    check("занятий ровно 16", len(lecture_files) == LESSONS,
          f"найдено {len(lecture_files)}")

    # ── 3. структура каждого занятия ──────────────────────────────────────
    for lp in lecture_files:
        text = lp.read_text(encoding="utf-8")
        for section in REQUIRED_SECTIONS:
            check(f"{lp.name} содержит {section!r}", section in text,
                  f"отсутствует раздел {section!r}")
        check(f"{lp.name} имеет навигацию", "**Навигация:**" in text,
              "нет блока навигации в конце занятия")

    # ── 4. все относительные ссылки разрешаются ───────────────────────────
    docs = [SYLLABUS_MD] + lecture_files + sorted((ROOT / "docs").glob("*.md"))
    docs += [p for p in (ROOT / "verification").glob("*.md")]
    total_links = 0
    for md in docs:
        if not md.is_file():
            continue
        for m in LINK_RE.finditer(md.read_text(encoding="utf-8", errors="replace")):
            target = m.group(2).split("#")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            total_links += 1
            check("ссылка разрешается", (md.parent / target).resolve().exists(),
                  f"{md.relative_to(ROOT)} -> {target}")

    # ── 5. документы, на которые опирается курс, на месте ─────────────────
    for rel in ("CORPUS.md", "PROVENANCE.md", "citations.md", "AGENTS.md",
                "LICENSE", "LICENSE-CONTENT.md", "verification/REPORT.md"):
        check(f"{rel} существует", (ROOT / rel).is_file(), "файл отсутствует")

    # ── корпус: манифесты обязаны нести хэши ─────────────────────────────
    # Курс, который публикует корпус, обязан публиковать его с хэшами:
    # без них повреждённая загрузка неотличима от исправной, и корпус
    # ставится вслепую. Пустой archive.url означает «ещё не опубликован»
    # (черновик) и допустим; заполненный url без sha256 — уже поломка.
    check("tools/corpus_fetch.py существует",
          (ROOT / "tools" / "corpus_fetch.py").is_file(),
          "tools/corpus_fetch.py отсутствует — корпус нечем получить")
    check("corpus-manifest.example.json существует",
          (ROOT / "corpus-manifest.example.json").is_file(),
          "нет образца манифеста текстов")

    for mname in ("index-manifest.json", "corpus-manifest.json"):
        mp = ROOT / mname
        if not mp.is_file():
            continue  # корпус может не публиковаться вовсе; это не поломка
        try:
            m = json.loads(mp.read_text(encoding="utf-8-sig"))
        except (ValueError, OSError) as e:
            check(f"{mname} разбирается", False, f"{type(e).__name__}: {e}")
            continue
        arch = m.get("archive") or {}
        url = arch.get("url") or ""
        if url:
            check(f"{mname}: у архива есть sha256", bool(arch.get("sha256")),
                  "url заполнен, но sha256 пуст — повреждённую загрузку не поймать")
            files = m.get("files") or []
            check(f"{mname}: перечислены файлы с хэшами",
                  bool(files) and all(f.get("sha256") for f in files),
                  "в files нет sha256 хотя бы у одного файла")
            check(f"{mname}: у каждого файла есть path",
                  all(f.get("path") for f in files),
                  "в files есть запись без path")

    # ── 6. контракт цитирования: координаты в отчёте верификации ──────────
    report = ROOT / "verification" / "REPORT.md"
    if report.is_file():
        text = report.read_text(encoding="utf-8")
        check("отчёт верификации не содержит неудач",
              "неудач: **0**" in text or "неудач: 0" in text,
              "в отчёте верификации есть неудачные цитаты")
        check("отчёт верификации содержит таблицу цитат",
              "| Лекция |" in text, "нет таблицы цитат")

    # ── отчёт ─────────────────────────────────────────────────────────────
    if args.json:
        print(json.dumps({
            "checks_run": checks_run,
            "problems": problems,
            "relative_links_checked": total_links,
            "lectures": len(lecture_files),
            "ok": not problems,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"Проверка курса: {checks_run} проверок, "
              f"{total_links} относительных ссылок, занятий {len(lecture_files)}")
        if problems:
            print(f"\nПроблем: {len(problems)}")
            for p in problems:
                print(f"  - {p}")
        else:
            print("Все проверки пройдены.")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
