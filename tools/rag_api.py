#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local RAG HTTP API for the course index (Annoy + embeddings + fastembed CPU).
Standalone, portable: reads the index from COURSE_INDEX_DIR (default
$COURSE_CORPUS_ROOT/index), port via RAG_PORT (default 8010).

Endpoints:
  GET /health
  GET /search?q=...&k=...&topic=...&threshold=...
  POST /search   (JSON {"q": "...", "k": 5})
"""
import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("COURSE_CORPUS_ROOT", "")
IDX = os.environ.get("COURSE_INDEX_DIR") or os.path.join(ROOT, "index")
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_t = None
_embn = None
_chunks = None
_model = None


def load():
    import annoy  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415
    global _t, _embn, _chunks
    cfg = json.load(open(os.path.join(IDX, "config.json"), encoding="utf-8"))
    _t = annoy.AnnoyIndex(cfg["dim"], cfg["metric"])
    _t.load(os.path.join(IDX, "annoy.index"))
    emb = np.load(os.path.join(IDX, "embeddings.npy"))
    _chunks = [json.loads(l) for l in open(os.path.join(IDX, "chunks.jsonl"), encoding="utf-8")]
    norm = np.linalg.norm(emb, axis=1, keepdims=True)
    norm[norm == 0] = 1e-9
    _embn = emb / norm
    print(f"[rag-api] index loaded: {len(_chunks)} chunks, dim {cfg['dim']}", flush=True)


def embed(q):
    import numpy as np  # noqa: PLC0415
    global _model
    if _model is None:
        from fastembed import TextEmbedding  # noqa: PLC0415
        _model = TextEmbedding(MODEL, providers=["CPUExecutionProvider"])
    v = np.array(list(_model.embed([q])), dtype=np.float32)[0]
    n = np.linalg.norm(v)
    return (v / n).tolist() if n else v.tolist()


def search(q, k=5, topic=None, threshold=0.0):
    import numpy as np  # noqa: PLC0415
    qv = embed(q)
    ids, dists = _t.get_nns_by_vector(qv, max(k * 4, 20), include_distances=True)
    out = []
    for i, d in zip(ids, dists):
        ch = _chunks[i]
        if topic and ch.get("topic") != topic:
            continue
        cos = float(np.dot(_embn[i], qv))
        score = max(0.0, min(1.0, (cos + 1) / 2))
        if score < threshold:
            continue
        out.append({"score": round(score, 4), "annoy_distance": round(float(d), 4),
                    "file": ch["file"], "topic": ch.get("topic"), "chunk_id": ch["chunk_id"],
                    "snippet": ch["text"][:300]})
        if len(out) >= k:
            break
    out.sort(key=lambda r: -r["score"])
    return out


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        p = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(p.query)
        try:
            if p.path == "/health":
                self._send(200, {"status": "ok", "service": "rag-philosophy-science",
                                 "chunks": len(_chunks) if _chunks else None})
                return
            if p.path == "/search":
                q = (qs.get("q") or [""])[0]
                if not q:
                    self._send(400, {"error": "missing q"})
                    return
                k = int((qs.get("k") or ["5"])[0])
                topic = (qs.get("topic") or [None])[0]
                threshold = float((qs.get("threshold") or ["0.0"])[0])
                self._send(200, {"query": q, "count": 0, "results": search(q, k, topic, threshold)})
                return
            self._send(404, {"error": "not found"})
        except Exception as e:  # noqa: BLE001
            self._send(500, {"error": str(e)[:300]})

    def do_POST(self):  # noqa: N802
        p = urllib.parse.urlparse(self.path)
        try:
            if p.path != "/search":
                self._send(404, {"error": "not found"})
                return
            ln = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(ln) if ln else b"{}"
            data = json.loads(raw.decode("utf-8") or "{}")
            q = (data.get("q") or "").strip()
            if not q:
                self._send(400, {"error": "missing q"})
                return
            k = int(data.get("k") or 5)
            self._send(200, {"query": q, "count": 0, "results": search(q, k=k)})
        except Exception as e:  # noqa: BLE001
            self._send(500, {"error": str(e)[:300]})

    def log_message(self, *args):  # noqa: A003
        pass


def main():
    port = int(os.environ.get("RAG_PORT", "8010"))
    if not os.path.exists(os.path.join(IDX, "config.json")):
        print(f"[rag-api] индекс не найден: {IDX}. Сначала: make index-fetch (см. docs/GOOGLE-DRIVE.md)", flush=True)
        return 2
    load()
    print(f"[rag-api] listening :{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    sys.exit(main())