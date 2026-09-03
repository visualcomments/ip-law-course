#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verifier (fuzzy): checks every quote cited in lectures/*.md against the
corpus (txt/) + chunk ids from the RAG index. OCR-tolerant via letter-only
normalization; accepted when coverage >= QUOTE_MIN_COVERAGE (0.92).
Writes verification/REPORT.md. Exit code 1 when any quote fails.

Dirs (env): COURSE_REPO_DIR (repo root; default: parent of tools),
COURSE_TXT_DIR (default $COURSE_CORPUS_ROOT/txt), COURSE_INDEX_DIR (default
$COURSE_CORPUS_ROOT/index).

Convention:
> **Цитата:** «...»
> **Источник:** `txt/<file>.txt` · фрагмент #<chunk_id>
"""
import difflib
import glob
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("COURSE_REPO_DIR") or os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.environ.get("COURSE_CORPUS_ROOT", "")
TXT = os.environ.get("COURSE_TXT_DIR") or os.path.join(ROOT, "txt")
IDX = os.environ.get("COURSE_INDEX_DIR") or os.path.join(ROOT, "index")
CHUNKS = os.path.join(IDX, "chunks.jsonl")
MIN_COVERAGE = float(os.environ.get("QUOTE_MIN_COVERAGE", "0.92"))


def letters(s: str) -> str:
    return re.sub(r"[^a-zа-яё]", "", (s or "").lower().replace("ё", "е"))


class Matcher:
    def __init__(self, text):
        self.text = text
        self.ltext = letters(text)

    def best_span(self, quote_letters):
        sm = difflib.SequenceMatcher(None, self.ltext, quote_letters, autojunk=False)
        m = sm.find_longest_match(0, len(self.ltext), 0, len(quote_letters))
        return m.size, m.a, m.b


def load_chunks_by_file():
    out = {}
    if not os.path.exists(CHUNKS):
        return out
    with open(CHUNKS, encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            out.setdefault(c["file"], []).append(c)
    return out


def main():
    chunks = load_chunks_by_file()
    file_cache = {}
    for p in glob.glob(os.path.join(TXT, "*.txt").replace("\\", "/")):
        base = os.path.basename(p)
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                file_cache[base] = Matcher(f.read())
        except OSError:
            pass
    chunk_mats = {}

    rows = []
    total = fails = 0
    for lp in sorted(glob.glob(os.path.join(REPO, "lectures", "*.md"))):
        with open(lp, encoding="utf-8") as f:
            text = f.read()
        for block in re.findall(r"(?m)^(>.*(?:\n>.*)*)", text):
            mq = re.search(r"\*\*Цитата:\*\*\s*(.*?)(?=\n\s*>?\s*\*\*Источник)", block, re.S)
            ms = re.search(r"\*\*Источник:\*\*\s*`?([^`·]+)`?\.?\s*·?\s*(?:фрагмент\s*#(\d+))?", block)
            if not (mq and ms):
                continue
            quote = mq.group(1).strip(" «»»«“”‘’\n\t")
            fname = ms.group(1).strip()
            cited = int(ms.group(2)) if ms.group(2) else None
            base = os.path.basename(fname)
            total += 1
            ql = letters(quote)
            mf = file_cache.get(base)
            if not mf or len(ql) < 20:
                rows.append((lp, quote, base, "FAIL: file/quote too short", None, 0.0))
                fails += 1
                continue
            size, a, b = mf.best_span(ql)
            cov = size / max(len(ql), 1)
            ok = cov >= MIN_COVERAGE
            found_chunk = None
            best_cov_chunk = 0.0
            if chunks.get(base):
                qpre = ql[:24]
                for c in chunks[base]:
                    if c["file"] != base:
                        continue
                    cm = chunk_mats.get(c["chunk_id"])
                    if cm is None:
                        cm = Matcher(c["text"])
                        chunk_mats[c["chunk_id"]] = cm
                    if qpre and qpre not in cm.ltext:
                        continue
                    cs, _, _ = cm.best_span(ql)
                    ccs = cs / max(len(ql), 1)
                    if ccs > best_cov_chunk:
                        best_cov_chunk, found_chunk = ccs, c["chunk_id"]
            status = "OK" if ok else "FAIL(cover %.2f)" % cov
            if ok and found_chunk is not None and found_chunk != cited:
                status += f" (cited #{cited}, actual #{found_chunk})"
            if not ok:
                fails += 1
            rows.append((lp, quote, base, status, found_chunk, cov))

    lines = [
        "# Отчёт проверки цитат",
        "",
        f"Проверено цитат: **{total}**; неудач: **{fails}**. Минимальное покрытие: {MIN_COVERAGE}.",
        "",
        "| Лекция | Цитата (начало) | Источник | Статус | Chunk | Покрытие |",
        "|---|---|---|---|---|---|",
    ]
    for lp, quote, base, status, cid, cov in rows:
        ln = os.path.basename(lp)
        qq = quote[:70].replace("\n", " ").replace("|", "/")
        lines.append(f"| {ln} | {qq} | {base} | {status} | "
                     f"{cid if cid is not None else '—'} | {cov:.2f} |")
    os.makedirs(os.path.join(REPO, "verification"), exist_ok=True)
    with open(os.path.join(REPO, "verification", "REPORT.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[verify_quotes] {total} quotes, {fails} fails -> verification/REPORT.md")
    for row in rows:
        if "FAIL" in row[3]:
            print(f"  FAIL: {row[3]} | {row[1][:70]}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())