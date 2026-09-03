#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Status: reports what is available for the agent — repo layout, corpus presence
(FALT_CORPUS_ROOT), RAG index, quote-verification state.

Usage:  python tools/status.py
"""
import glob
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.environ.get("FALT_CORPUS_ROOT")


def main():
    if not ROOT:
        print("корпус не настроен: установите FALT_CORPUS_ROOT (см. CORPUS.md)")
        return 2
    print("== Репозиторий курса ==")
    print(f"repo root: {REPO}")
    lecs = sorted(glob.glob(os.path.join(REPO, "lectures", "*.md")))
    print(f"занятий: {len(lecs)}")
    if os.path.exists(os.path.join(REPO, "verification", "REPORT.md")):
        head = open(os.path.join(REPO, "verification", "REPORT.md"), encoding="utf-8").read()
        for l in head.splitlines()[:4]:
            print("  " + l)
    sy = os.path.join(REPO, "syllabus.json")
    if os.path.exists(sy):
        d = json.load(open(sy, encoding="utf-8"))
        print(f"syllabus.json: {d['meta']['sessions_total']} занятий, "
              f"модулей: {len(d['modules'])}")
    print()
    print("== Локальный корпус ==")
    ntxt = len(glob.glob(os.path.join(ROOT, "txt", "*.txt")))
    idx = os.path.join(ROOT, "index", "config.json")
    print(f"корпус root: {ROOT}")
    print(f"txt файлов: {ntxt}")
    if os.path.exists(idx):
        c = json.load(open(idx, encoding="utf-8"))
        print(f"RAG-индекс: {c.get('n_chunks')} чанков, {c.get('n_files')} файлов, "
              f"backend: {c.get('backend')}")
    else:
        print("RAG-индекс: НЕ НАЙДЕН (нужен scripts/rag_build*.py и корпус)")
    api = os.path.join(ROOT, "scripts", "rag_api.py")
    print(f"RAG-API скрипт: {'есть' if os.path.exists(api) else 'нет'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())