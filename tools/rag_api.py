#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local HTTP API for exact search over the dense course index.

Reads the index from COURSE_INDEX_DIR and the port from --port or RAG_PORT.

Endpoints:
  GET /health
  GET /search?q=...&k=...&topic=...&threshold=...
  POST /search   (JSON {"q": "...", "k": 5})
"""
import argparse
import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from rag_index import create_query_encoder, load_index, search_index

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("COURSE_CORPUS_ROOT", "")
IDX = os.environ.get("COURSE_INDEX_DIR") or os.path.join(ROOT, "index")

_embn = None
_chunks = None
_model = None
_model_name = None


def load():
    global _embn, _chunks, _model_name
    cfg, _embn, _chunks = load_index(IDX)
    _model_name = cfg["model"]
    print(
        f"[rag-api] index loaded: {len(_chunks)} chunks, dim {cfg['dim']}",
        flush=True,
    )


def embed(q):
    import numpy as np  # noqa: PLC0415
    global _model
    if _model is None:
        _model = create_query_encoder(_model_name)
    v = np.array(list(_model.embed([q])), dtype=np.float32)[0]
    n = np.linalg.norm(v)
    return (v / n).tolist() if n else v.tolist()


def search(q, k=5, topic=None, threshold=0.0):
    import numpy as np  # noqa: PLC0415
    qv = np.array(embed(q), dtype=np.float32)
    return search_index(_embn, _chunks, qv, k, topic, threshold)


def search_response(q, k=5, topic=None, threshold=0.0):
    results = search(q, k, topic, threshold)
    return {"query": q, "count": len(results), "results": results}


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
                self._send(
                    200,
                    {
                        "status": "ok",
                        "service": "rag-philosophy-science",
                        "chunks": len(_chunks) if _chunks else None,
                    },
                )
                return
            if p.path == "/search":
                q = (qs.get("q") or [""])[0]
                if not q:
                    self._send(400, {"error": "missing q"})
                    return
                k = int((qs.get("k") or ["5"])[0])
                topic = (qs.get("topic") or [None])[0]
                threshold = float((qs.get("threshold") or ["0.0"])[0])
                self._send(200, search_response(q, k, topic, threshold))
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
            k = int(data.get("k", 5))
            topic = data.get("topic") or None
            threshold = float(data.get("threshold") or 0.0)
            self._send(200, search_response(q, k, topic, threshold))
        except Exception as e:  # noqa: BLE001
            self._send(500, {"error": str(e)[:300]})

    def log_message(self, *args):  # noqa: A003
        pass


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("RAG_PORT", "8010"))
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not os.path.exists(os.path.join(IDX, "config.json")):
        print(
            f"[rag-api] индекс не найден: {IDX}. Сначала: make corpus-fetch "
            "(см. docs/GOOGLE-DRIVE.md)",
            flush=True,
        )
        return 2
    load()
    print(f"[rag-api] listening :{args.port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    sys.exit(main())
