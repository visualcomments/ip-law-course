#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session material: prints a single session (NN) — its full lecture file path,
topic, quotes with coordinates, and sources. Corpus-independent: works purely
from the repository content.

Usage:
  python tools/session_material.py 18
"""
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))  # course/


def find_session(n):
    pat = os.path.join(REPO, "lectures", f"{n:02d}_*.md")
    files = sorted(glob.glob(pat))
    return files[0] if files else None


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    fp = find_session(n)
    if not fp:
        print(f"[session] занятие {n:02d} не найдено (ищи NN_*.md в lectures/)")
        return 1
    text = open(fp, encoding="utf-8").read()
    title = text.splitlines()[0].lstrip("# ").strip()
    print(f"# {title}\n")
    print(f"Файл: `lectures/{os.path.basename(fp)}`\n")
    m = re.search(r"\*\*[^\n]*Семестр[^\n]*\*\*", text)
    if m:
        print(m.group(0) + "\n")
    quotes = re.findall(r"\*\*Цитата:\*\*\s*«(.*?)»", text, re.S)
    srcs = re.findall(r"\*\*Источник:\*\*\s*`([^`]+)`\s*·\s*фрагмент\s*#(\d+)", text)
    print(f"Прямые цитаты из корпуса: {len(srcs)}\n")
    for (q, (fname, ch)) in zip(quotes, srcs):
        print(f"- {fname} · фрагмент #{ch}")
        print(f"  «{q.strip()[:160]}»\n")
    # sources list (unique files)
    files = sorted({f for f, _ in srcs})
    print("Источники занятия:", ", ".join(f"`{f}`" for f in files) if files else "—")
    return 0


if __name__ == "__main__":
    sys.exit(main())