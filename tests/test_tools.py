#!/usr/bin/env python3
"""Тесты инструментов курса.

Проверяют, что инструменты в `tools/` работают на реальных данных курса:
валидатор целостности проходит, поиск по корпусу находит известные нормы,
верификация цитат не находит расхождений.

Запуск:
    python3 tests/test_tools.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"

_passed = 0
_failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    global _passed
    if condition:
        _passed += 1
        print(f"  ok   {name}")
    else:
        _failures.append(name)
        print(f"  FAIL {name}  {detail}")


def run_tool(script: str, *args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOLS / script), *args],
        capture_output=True, text=True, cwd=ROOT, timeout=timeout)


def main() -> int:
    print("[целостность курса]")

    r = run_tool("validate_course.py")
    check("валидатор курса завершается успешно", r.returncode == 0,
          r.stdout[-200:] + r.stderr[-200:])
    check("валидатор сообщает о пройденных проверках",
          "Все проверки пройдены" in r.stdout, r.stdout[-200:])

    r = run_tool("validate_course.py", "--json")
    if r.returncode == 0:
        try:
            data = json.loads(r.stdout)
            check("валидатор выдаёт машиночитаемый отчёт",
                  data.get("ok") is True, str(data)[:200])
            check("валидатор проверяет 16 занятий",
                  data.get("lectures") == 16, str(data.get("lectures")))
            check("валидатор проверил относительные ссылки",
                  data.get("relative_links_checked", 0) > 0,
                  str(data.get("relative_links_checked")))
        except json.JSONDecodeError as e:
            check("валидатор выдаёт корректный JSON", False, str(e))
    else:
        check("валидатор работает с --json", False, r.stderr[-200:])

    print("\n[структура курса]")

    lectures = sorted((ROOT / "lectures").glob("*.md"))
    check("занятий ровно 16", len(lectures) == 16, f"найдено {len(lectures)}")

    required = ("## Цели занятия", "## Тезис", "## Источники и свидетельства",
                "## Вопросы для самопроверки", "## Задания")
    for lp in lectures:
        text = lp.read_text(encoding="utf-8")
        missing = [s for s in required if s not in text]
        check(f"{lp.name} содержит все обязательные разделы",
              not missing, f"нет: {missing}")

    print("\n[программа и корпус]")

    syllabus_md = (ROOT / "syllabus.md").read_text(encoding="utf-8")
    linked = sum(1 for lp in lectures if lp.name in syllabus_md)
    check("каждое занятие связано с программой", linked == 16,
          f"связано {linked} из 16")

    syllabus_json = ROOT / "syllabus.json"
    if syllabus_json.is_file():
        try:
            data = json.loads(syllabus_json.read_text(encoding="utf-8"))
            check("syllabus.json разбирается", isinstance(data, dict), "не объект")
        except json.JSONDecodeError as e:
            check("syllabus.json разбирается", False, str(e))

    for doc in ("CORPUS.md", "PROVENANCE.md", "citations.md", "AGENTS.md",
                "LICENSE", "LICENSE-CONTENT.md", "verification/REPORT.md"):
        check(f"{doc} на месте", (ROOT / doc).is_file(), "файл отсутствует")

    print("\n[отчёт верификации цитат]")
    report = ROOT / "verification" / "REPORT.md"
    if report.is_file():
        text = report.read_text(encoding="utf-8")
        check("верификация без неудач", "неудач: **0**" in text, "есть неудачи")
        check("отчёт содержит таблицу цитат", "| Лекция |" in text, "нет таблицы")

    print(f"\n{_passed} passed, {len(_failures)} failed")
    if _failures:
        for f in _failures:
            print(f"  - {f}")
        return 1
    return 0


def test_course_structure() -> None:
    """Pytest entry point: the whole suite must pass."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
