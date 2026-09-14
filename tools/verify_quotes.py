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


def find_citations():
    citations = []
    for lecture_path in sorted(glob.glob(os.path.join(REPO, "lectures", "*.md"))):
        with open(lecture_path, encoding="utf-8") as f:
            text = f.read()
        for block in re.findall(r"(?m)^(>.*(?:\n>.*)*)", text):
            quote_match = re.search(
                r"\*\*Цитата:\*\*\s*(.*?)(?=\n\s*>?\s*\*\*Источник)", block, re.S
            )
            source_match = re.search(
                r"\*\*Источник:\*\*\s*`?([^`·]+)`?\.?\s*·?\s*"
                r"(?:фрагмент\s*#(\d+))?",
                block,
            )
            if not (quote_match and source_match):
                continue
            quote = quote_match.group(1).strip(" «»»«“”‘’\n\t")
            source = source_match.group(1).strip()
            chunk_id = int(source_match.group(2)) if source_match.group(2) else None
            citations.append((lecture_path, quote, os.path.basename(source), chunk_id))
    return citations


def main():
    chunks = load_chunks_by_file()
    citations = find_citations()
    required_sources = {base for _lp, _quote, base, _cid in citations}
    missing_index_sources = sorted(required_sources - chunks.keys())
    if missing_index_sources:
        print(
            f"[verify_quotes] индекс неполон: нет {len(missing_index_sources)} файлов. "
            "Отчёт не тронут (установка корпуса — CORPUS.md)"
        )
        return 2

    file_cache = {}
    for p in glob.glob(os.path.join(TXT, "*.txt").replace("\\", "/")):
        base = os.path.basename(p)
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                file_cache[base] = Matcher(f.read())
        except OSError:
            pass
    missing_sources = sorted(required_sources - file_cache.keys())
    if missing_sources:
        print(
            f"[verify_quotes] корпус неполон: нет {len(missing_sources)} файлов. "
            "Отчёт не тронут (установка корпуса — CORPUS.md)"
        )
        return 2
    chunk_mats = {}

    rows = []
    total = fails = 0
    for lp, quote, base, cited in citations:
        total += 1
        ql = letters(quote)
        if len(ql) < 20:
            rows.append((lp, quote, base, "FAIL: quote too short", None, 0.0))
            fails += 1
            continue

        size, _start, _quote_start = file_cache[base].best_span(ql)
        coverage = size / len(ql)
        found_chunk = None
        best_chunk_coverage = 0.0
        cited_coverage = 0.0
        for chunk in chunks.get(base, []):
            key = (base, chunk["chunk_id"])
            matcher = chunk_mats.get(key)
            if matcher is None:
                matcher = Matcher(chunk["text"])
                chunk_mats[key] = matcher
            chunk_size, _chunk_start, _chunk_quote_start = matcher.best_span(ql)
            chunk_coverage = chunk_size / len(ql)
            if chunk["chunk_id"] == cited:
                cited_coverage = chunk_coverage
            if chunk_coverage > best_chunk_coverage:
                best_chunk_coverage = chunk_coverage
                found_chunk = chunk["chunk_id"]

        if coverage < MIN_COVERAGE:
            status = f"FAIL: покрытие {coverage:.2f}"
        elif cited is None:
            status = f"FAIL: нет координаты, найден #{found_chunk}"
        elif cited_coverage < MIN_COVERAGE:
            status = f"FAIL: указан #{cited}, найден #{found_chunk}"
        else:
            status = "OK"

        if status.startswith("FAIL"):
            fails += 1
        rows.append((lp, quote, base, status, found_chunk, coverage))

    lines = [
        "# Отчёт проверки цитат",
        "",
        f"Проверено цитат: **{total}**; неудач: **{fails}**. "
        f"Минимальное покрытие: {MIN_COVERAGE}.",
        "",
        "| Лекция | Цитата (начало) | Источник | Статус | "
        "Фрагмент | Покрытие |",
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
    print(f"[verify_quotes] {total} цитат, {fails} ошибок -> verification/REPORT.md")
    for row in rows:
        if "FAIL" in row[3]:
            print(f"  FAIL: {row[3]} | {row[1][:70]}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
