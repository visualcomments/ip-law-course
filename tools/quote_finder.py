#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
quote_finder: locate a phrase/substring across the corpus txt/ files.
Useful for gathering verbatim PD quotes. Prints file + line + context.

Usage:  python tools/quote_finder.py "чистого разума"
Dirs: COURSE_TXT_DIR (default $COURSE_CORPUS_ROOT/txt).
"""
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.environ.get("COURSE_CORPUS_ROOT", "")
TXT = os.environ.get("COURSE_TXT_DIR") or os.path.join(ROOT, "txt")


def main():
    q = sys.argv[1] if len(sys.argv) > 1 else ""
    if not q:
        print("Укажите фразу для поиска")
        return 2
    rq = re.compile(re.escape(q), re.IGNORECASE)
    found = 0
    for p in sorted(glob.glob(os.path.join(TXT, "*.txt").replace("\\", "/"))):
        try:
            t = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in rq.finditer(t):
            a = max(0, m.start() - 140)
            b = min(len(t), m.end() + 200)
            snip = re.sub(r"\s+", " ", t[a:b]).strip()
            print(f"{os.path.basename(p)}:")
            print(f"  …{snip}…")
            found += 1
            if found >= 8:
                break
        if found >= 8:
            break
    print(f"[quote_finder] найдено: {found}")
    return 0 if found else 1


if __name__ == "__main__":
    sys.exit(main())