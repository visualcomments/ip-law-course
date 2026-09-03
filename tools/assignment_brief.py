#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assignment brief: prints the «Вопросы для самопроверки» and «Задания»
sections of a session (NN). Use to break down assignments for the learner.

Usage:
  python tools/assignment_brief.py 18
"""
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    pat = os.path.join(REPO, "lectures", f"{n:02d}_*.md")
    files = sorted(glob.glob(pat))
    if not files:
        print(f"[tools] занятие {n:02d} не найдено")
        return 1
    text = open(files[0], encoding="utf-8").read()
    title = text.splitlines()[0].lstrip("# ").strip()
    print(f"# {title}\n")
    for section in ("Вопросы для самопроверки", "Задания"):
        m = re.search(r"## " + section + r"(.*?)(?=\n## |\Z)", text, re.S)
        if m:
            print(f"## {section}")
            print(m.group(1).strip() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())