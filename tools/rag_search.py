#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semantic search over the course RAG index (embeddings + Annoy).
Requires the index installed (see docs/GOOGLE-DRIVE.md, make index-fetch)
and a query-embedding backend: fastembed (recommended) — pure CPU.

Dirs (env): COURSE_INDEX_DIR (default $COURSE_CORPUS_ROOT/index).

Usage:
  python tools/rag_search.py "Кант критика чистого разума" -k 5 [--topic ...] [--json]
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("COURSE_CORPUS_ROOT", "")
IDX = os.environ.get("COURSE_INDEX_DIR") or os.path.join(ROOT, "index")
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def load():
    import annoy  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415
    cfg = json.load(open(os.path.join(IDX, "config.json"), encoding="utf-8"))
    t = annoy.AnnoyIndex(cfg["dim"], cfg["metric"])
    t.load(os.path.join(IDX, "annoy.index"))
    emb = np.load(os.path.join(IDX, "embeddings.npy"))
    chunks = [json.loads(l) for l in open(os.path.join(IDX, "chunks.jsonl"), encoding="utf-8")]
    norm = np.linalg.norm(emb, axis=1, keepdims=True)
    norm[norm == 0] = 1e-9
    return cfg, t, emb / norm, chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--topic", default=None)
    ap.add_argument("--threshold", type=float, default=0.0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(os.path.join(IDX, "config.json")):
        sys.stderr.write(f"[rag_search] индекс не найден в {IDX}\n"
                         "Выполните: make index-fetch URL=<ссылка Google Диска> (см. docs/GOOGLE-DRIVE.md)\n")
        return 2
    try:
        cfg, t, embn, chunks = load()
        import numpy as np  # noqa: PLC0415
        from fastembed import TextEmbedding  # noqa: PLC0415
        model = TextEmbedding(MODEL, providers=["CPUExecutionProvider"])
    except ImportError as e:
        sys.stderr.write(f"[rag_search] нужны зависимости (numpy, annoy, fastembed): {e}\n")
        return 2

    v = np.array(list(model.embed([a.query])), dtype=np.float32)[0]
    vn = v / max(float(np.linalg.norm(v)), 1e-9)

    ids, dists = t.get_nns_by_vector(vn.tolist(), max(a.k * 4, 20), include_distances=True)
    out = []
    for i, d in zip(ids, dists):
        ch = chunks[i]
        if a.topic and ch.get("topic") != a.topic:
            continue
        cos = float(np.dot(embn[i], vn))
        score = max(0.0, min(1.0, (cos + 1) / 2))
        if score < a.threshold:
            continue
        out.append({"score": round(score, 4), "annoy_distance": round(float(d), 4),
                    "file": ch["file"], "topic": ch.get("topic"), "chunk_id": ch["chunk_id"],
                    "snippet": ch["text"][:300]})
        if len(out) >= a.k:
            break
    out.sort(key=lambda r: -r["score"])
    if a.json:
        print(json.dumps({"query": a.query, "count": len(out), "results": out},
                         ensure_ascii=False, indent=1))
        return 0
    print(f"query: {a.query} | count: {len(out)}")
    for r in out:
        print(f"  {r['score']:.3f} | {r['file']} | фрагмент #{r['chunk_id']}")
        print(f"    {r['snippet'][:110]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())