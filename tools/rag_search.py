#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Semantic search over the dense course index.

Requires an installed index and the fastembed query encoder.

Dirs (env): COURSE_INDEX_DIR (default $COURSE_CORPUS_ROOT/index).

Usage:
  python tools/rag_search.py "критерии патентоспособности" -k 5 [--json]
"""
import argparse
import json
import os
import sys

from rag_index import create_query_encoder, load_index, search_index

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("COURSE_CORPUS_ROOT", "")
IDX = os.environ.get("COURSE_INDEX_DIR") or os.path.join(ROOT, "index")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--topic", default=None)
    ap.add_argument("--threshold", type=float, default=0.0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(os.path.join(IDX, "config.json")):
        sys.stderr.write(
            f"[rag_search] индекс не найден в {IDX}\n"
            "Выполните: make corpus-fetch (см. docs/GOOGLE-DRIVE.md)\n"
        )
        return 2
    try:
        config, embeddings, chunks = load_index(IDX)
        import numpy as np  # noqa: PLC0415
        model = create_query_encoder(config["model"])
    except ImportError as e:
        sys.stderr.write(
            f"[rag_search] нужны зависимости (numpy, fastembed): {e}\n"
        )
        return 2

    vector = np.array(list(model.embed([a.query])), dtype=np.float32)[0]
    try:
        out = search_index(
            embeddings, chunks, vector, a.k, a.topic, a.threshold
        )
    except ValueError as e:
        sys.stderr.write(f"[rag_search] {e}\n")
        return 2
    if a.json:
        print(
            json.dumps(
                {"query": a.query, "count": len(out), "results": out},
                ensure_ascii=False,
                indent=1,
            )
        )
        return 0
    print(f"query: {a.query} | count: {len(out)}")
    for r in out:
        print(f"  {r['score']:.3f} | {r['file']} | фрагмент #{r['chunk_id']}")
        print(f"    {r['snippet'][:110]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
