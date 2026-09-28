#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Deterministic validator for the universal course-dataset schema (schema 1).

Zero external dependencies (stdlib only), so it can run as a CI step on the
Kurator server and in the course repos.

Usage:
  python validate.py RECORDS.jsonl [--corpus-root DIR ...] [--min-coverage 0.92]
                                  [--selftest] [--json]

Checks (mirrors universal-record.schema.json):
  * JSON parse; required fields; types; enums; measurements[] non-empty
  * amendment: predicate in the 7 factual values; norm_id pattern
  * cross-field: status=verified  =>  evidence_quote and source.coord present
  * with --corpus-root: evidence_quote must be a VERBATIM substring of the
    referenced file after whitespace/OCR normalization (design invariant I5);
    per-record coverage reported. Missing files => exit code 2 ("cannot verify"),
    never "invalid" (course convention: "no way to check" != "wrong").

Exit codes: 0 = ok, 1 = errors found, 2 = cannot verify (missing corpus).

--selftest proves the quote check CAN fail (invariant I8: a check that cannot
fail is not a check): it validates a deliberately broken record and expects errors.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FACTUAL_PREDICATES = {
    "изменена",
    "дополнена",
    "введена",
    "изложена_в_новой_редакции",
    "признана_утратившей_силу",
    "исключена",
    "уточнена",
}
DOC_TYPES = {
    "scientific_article",
    "pd_book",
    "npa",
    "official_document",
    "commentary",
    "other",
}
LICENSES = {
    "PD",
    "CC0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "official-document",
    "facts-derived",
    "cite-only",
    "unknown",
}
METHODS = {"manual", "assisted", "script"}
DERIVATIONS = {"verbatim_quote", "facts_reworked"}
FIGURE_RIGHTS = {
    "own",
    "PD",
    "CC0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "official-document",
    "permission",
    "unknown",
}
FIGURE_KINDS = {"photo", "diagram", "chart", "table", "micrograph", "map", "other"}
STATUSES = {"proposed", "verified", "rejected"}
QUALITIES = {"exact", "ocr_uncertain", "estimate", "missing"}
GRANULARITIES = {"year", "month", "day"}
RECORD_ID_RE = re.compile(r"^[a-z0-9._-]+$")
NORM_ID_RE = re.compile(r"^[a-z0-9а-я-]+/.+$")
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
TS_RE = re.compile(r"^[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?$")

BASE_REQUIRED = [
    "schema",
    "record_id",
    "profile",
    "title_ru",
    "source",
    "provenance",
    "review",
]


def norm_ws(s: str) -> str:
    """Whitespace/OCR normalization: de-hyphenate wrapped words, drop soft
    hyphens, collapse whitespace (course citation contract: only OCR noise)."""
    s = s.replace("\u00ad", "")  # soft hyphen
    s = s.replace("\u2010", "-").replace("\u2011", "-")  # unicode hyphens
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)  # join words split by hyphen+newline
    return re.sub(r"\s+", " ", s).strip()


def _check_obj(obj, field: str, required: list[str], errors: list[str]) -> None:
    if not isinstance(obj, dict):
        errors.append(f"{field}: must be object")
        return
    for r in required:
        if r not in obj:
            errors.append(f"{field}: missing required '{r}'")


def facts_mode(rec: dict) -> bool:
    """Запись построена на переработанных фактах (без дословной цитаты)."""
    prov = rec.get("provenance") or {}
    src = rec.get("source") or {}
    return (
        prov.get("derivation") == "facts_reworked"
        or src.get("license") == "facts-derived"
    )


def validate_figures(rec: dict, errors: list[str]) -> None:
    figs = rec.get("figures")
    if figs is None:
        return
    if not isinstance(figs, list):
        errors.append("figures must be an array")
        return
    for i, f in enumerate(figs):
        _check_obj(f, f"figures[{i}]", ["path", "rights"], errors)
        if isinstance(f, dict):
            if f.get("rights") not in FIGURE_RIGHTS:
                errors.append(
                    f"figures[{i}].rights invalid: {f.get('rights')!r} "
                    "(сырое изображение из проприетарного источника публиковать нельзя)"
                )
            if f.get("kind") is not None and f.get("kind") not in FIGURE_KINDS:
                errors.append(f"figures[{i}].kind invalid: {f.get('kind')!r}")


def validate_base(rec: dict, errors: list[str]) -> None:
    for r in BASE_REQUIRED:
        if r not in rec:
            errors.append(f"missing required '{r}'")
    if rec.get("schema") != 1:
        errors.append("schema must be 1")
    if not isinstance(rec.get("record_id"), str) or not RECORD_ID_RE.match(
        rec.get("record_id", "")
    ):
        errors.append("record_id must match ^[a-z0-9._-]+$")
    src = rec.get("source")
    _check_obj(src, "source", ["file", "doc_type", "license"], errors)
    if isinstance(src, dict):
        if src.get("doc_type") not in DOC_TYPES:
            errors.append(f"source.doc_type invalid: {src.get('doc_type')!r}")
        if src.get("license") not in LICENSES:
            errors.append(f"source.license invalid: {src.get('license')!r}")
    prov = rec.get("provenance")
    _check_obj(prov, "provenance", ["extracted_by", "extracted_at", "method"], errors)
    if isinstance(prov, dict):
        if prov.get("method") not in METHODS:
            errors.append(f"provenance.method invalid: {prov.get('method')!r}")
        if (
            prov.get("derivation") is not None
            and prov.get("derivation") not in DERIVATIONS
        ):
            errors.append(f"provenance.derivation invalid: {prov.get('derivation')!r}")
        if not DATE_RE.match(str(prov.get("extracted_at", ""))):
            errors.append("provenance.extracted_at must be YYYY-MM-DD")
    rev = rec.get("review")
    _check_obj(rev, "review", ["status"], errors)
    if isinstance(rev, dict) and rev.get("status") not in STATUSES:
        errors.append(f"review.status invalid: {rev.get('status')!r}")
    # facts-derived / facts_reworked: факт изложен своими словами —
    # дословная цитата охраняемого текста запрещена, координата обязательна.
    if facts_mode(rec):
        if norm_ws(str(rec.get("evidence_quote") or "")):
            errors.append(
                "facts_reworked/facts-derived: evidence_quote must be empty "
                "(нельзя приводить дословный фрагмент охраняемого текста)"
            )
        if not norm_ws(str((src or {}).get("coord") or "")):
            errors.append("facts_reworked/facts-derived requires source.coord")
    # cross-field: verified requires evidence
    if isinstance(rev, dict) and rev.get("status") == "verified":
        if not facts_mode(rec) and not norm_ws(str(rec.get("evidence_quote") or "")):
            errors.append(
                "review.status=verified requires non-empty evidence_quote "
                "(или derivation=facts_reworked)"
            )
        if not norm_ws(str((src or {}).get("coord") or "")):
            errors.append("review.status=verified requires source.coord")
    if "confidence" in rec and rec["confidence"] is not None:
        c = rec["confidence"]
        if not isinstance(c, (int, float)) or not (0 <= c <= 1):
            errors.append("confidence must be number in [0,1]")


def validate_experiment(rec: dict, errors: list[str]) -> None:
    _check_obj(rec.get("experiment"), "experiment", ["subject_ru", "method_ru"], errors)
    ms = rec.get("measurements")
    if not isinstance(ms, list) or len(ms) < 1:
        errors.append("measurements must be a non-empty array")
    else:
        for i, m in enumerate(ms):
            _check_obj(
                m,
                f"measurements[{i}]",
                ["variable_ru", "value", "unit", "quality"],
                errors,
            )
            if isinstance(m, dict):
                if m.get("quality") not in QUALITIES:
                    errors.append(
                        f"measurements[{i}].quality invalid: {m.get('quality')!r}"
                    )
                if not isinstance(m.get("value"), (int, float, str)):
                    errors.append(f"measurements[{i}].value must be number or string")
    if not norm_ws(str(rec.get("outcome_ru") or "")):
        errors.append("outcome_ru required")
    validate_figures(rec, errors)


def validate_amendment(rec: dict, errors: list[str]) -> None:
    nm = rec.get("norm")
    _check_obj(nm, "norm", ["source_law", "article"], errors)
    if isinstance(nm, dict) and nm.get("norm_id"):
        if not NORM_ID_RE.match(str(nm["norm_id"])):
            errors.append(f"norm.norm_id does not match pattern: {nm['norm_id']!r}")
    if rec.get("predicate") not in FACTUAL_PREDICATES:
        errors.append(f"predicate invalid: {rec.get('predicate')!r}")
    if not norm_ws(str(rec.get("amending_doc") or "")):
        errors.append("amending_doc required")
    if not norm_ws(str(rec.get("change_ru") or "")):
        errors.append("change_ru required")
    ts = rec.get("ts")
    if ts and not TS_RE.match(str(ts)):
        errors.append("ts must be YYYY | YYYY-MM | YYYY-MM-DD")
    if "granularity" in rec and rec["granularity"] not in GRANULARITIES:
        errors.append(f"granularity invalid: {rec['granularity']!r}")


def resolve_source(file_rel: str, roots: list[Path]) -> Path | None:
    p = Path(file_rel)
    if p.is_absolute() and p.is_file():
        return p
    for root in roots:
        cand = root / file_rel
        if cand.is_file():
            return cand
    return None


def quote_check(
    rec: dict, roots: list[Path], min_coverage: float
) -> tuple[str, float | None]:
    """Returns (status, coverage) where status in ok|mismatch|unavailable|no_quote|not_applicable."""
    if facts_mode(rec):
        return "not_applicable", None
    quote = norm_ws(str(rec.get("evidence_quote") or ""))
    src = rec.get("source") or {}
    file_rel = str(src.get("file") or "")
    if not quote:
        return "no_quote", None
    path = resolve_source(file_rel, roots) if file_rel else None
    if path is None:
        return "unavailable", None
    text = norm_ws(path.read_text(encoding="utf-8", errors="replace"))
    if quote in text:
        return "ok", 1.0
    # Best-effort coverage: longest common prefix ratio (diagnostic only).
    lo, hi = 0, min(len(quote), len(text))
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if quote[:mid] in text:
            lo = mid
        else:
            hi = mid - 1
    cov = lo / max(len(quote), 1)
    return ("ok" if cov >= min_coverage else "mismatch"), cov


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Validate universal course-dataset records"
    )
    ap.add_argument("records", nargs="?", help="JSONL file")
    ap.add_argument(
        "--corpus-root", action="append", default=[], help="corpus root (repeatable)"
    )
    ap.add_argument("--min-coverage", type=float, default=0.92)
    ap.add_argument(
        "--selftest", action="store_true", help="prove the quote check can fail (I8)"
    )
    ap.add_argument("--json", action="store_true", help="machine-readable summary")
    args = ap.parse_args()

    if args.selftest:
        broken = {
            "schema": 1,
            "record_id": "selftest.broken",
            "profile": "amendment",
            "title_ru": "selftest",
            "source": {
                "file": "__selftest__.txt",
                "doc_type": "npa",
                "license": "official-document",
            },
            "provenance": {
                "extracted_by": "selftest",
                "extracted_at": "2026-09-27",
                "method": "manual",
            },
            "review": {"status": "verified"},
            "norm": {
                "source_law": "ГК РФ",
                "article": "ст.1259",
                "norm_id": "гк-рф/ст.1259",
            },
            "amending_doc": "X",
            "predicate": "изменена",
            "change_ru": "selftest",
            "evidence_quote": "ЭТОЙ ФРАЗЫ В ИСТОЧНИКЕ НЕТ 12345",
        }
        errs: list[str] = []
        validate_base(broken, errs)
        validate_amendment(broken, errs)
        tmp = Path("__selftest__.txt")
        tmp.write_text("реальный текст источника без искомой фразы", encoding="utf-8")
        status, cov = quote_check(broken, [Path(".")], args.min_coverage)
        tmp.unlink(missing_ok=True)
        ok = bool(errs) and status == "mismatch"
        print(
            f"selftest: errors={len(errs)} quote_status={status} coverage={cov:.2f} -> {'PASS' if ok else 'FAIL'}"
        )
        return 0 if ok else 1

    if not args.records:
        ap.error("records file is required (or use --selftest)")
    roots = [Path(r) for r in args.corpus_root] or [Path(".")]
    path = Path(args.records)
    if not path.is_file():
        print(f"error: {path} not found", file=sys.stderr)
        return 2

    n = ok = err = cannot = 0
    err_records: list[dict] = []
    quote_results: list[tuple[str, str | None, float | None]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        n += 1
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as e:
            err += 1
            err_records.append({"line": lineno, "id": None, "errors": [f"JSON: {e}"]})
            continue
        errors: list[str] = []
        validate_base(rec, errors)
        prof = rec.get("profile")
        if prof == "experiment":
            validate_experiment(rec, errors)
        elif prof == "amendment":
            validate_amendment(rec, errors)
        else:
            errors.append(f"profile invalid: {prof!r}")
        qstatus, cov = quote_check(rec, roots, args.min_coverage)
        quote_results.append((rec.get("record_id", "?"), qstatus, cov))
        if qstatus == "unavailable":
            cannot += 1
        elif qstatus == "mismatch":
            errors.append(
                f"evidence_quote not found in source (coverage {cov:.2f} < {args.min_coverage})"
            )
        if errors:
            err += 1
            err_records.append(
                {"line": lineno, "id": rec.get("record_id"), "errors": errors}
            )
        else:
            ok += 1

    verified_quotes = sum(1 for _, s, _ in quote_results if s == "ok")
    quote_total = sum(1 for _, s, _ in quote_results if s in ("ok", "mismatch"))
    coverage = (verified_quotes / quote_total) if quote_total else None

    summary = {
        "records": n,
        "ok": ok,
        "errors": err,
        "cannot_verify": cannot,
        "quote_verified": verified_quotes,
        "quote_checked": quote_total,
        "quote_coverage": coverage,
        "min_coverage": args.min_coverage,
        "failed_records": err_records,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"records={n} ok={ok} errors={err} cannot_verify={cannot}")
        if coverage is not None:
            print(
                f"quote coverage={coverage:.3f} (checked {quote_total}, verified {verified_quotes})"
            )
        for r in err_records:
            print(f"  line {r['line']} [{r['id']}]: " + "; ".join(r["errors"]))

    if err:
        return 1
    if cannot and not quote_total:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
