import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import rag_api
from rag_index import search_index


def chunks(count):
    return [
        {
            "file": f"file-{i}.txt",
            "topic": "topic",
            "chunk_id": i,
            "text": f"text {i}",
        }
        for i in range(count)
    ]


class SearchTests(unittest.TestCase):
    def test_orders_results_and_filters_topic(self):
        embeddings = np.array(
            [[1.0, 0.0], [0.8, 0.6], [-1.0, 0.0]], dtype=np.float32
        )
        data = chunks(3)
        data[0]["topic"] = "other"

        results = search_index(embeddings, data, [1.0, 0.0], k=2, topic="topic")

        self.assertEqual([result["chunk_id"] for result in results], [1, 2])

    def test_clamps_cosine_before_distance(self):
        embeddings = np.array([[1.0000002, 0.0]], dtype=np.float32)

        result = search_index(embeddings, chunks(1), [1.0, 0.0], k=1)[0]

        self.assertEqual(result["score"], 1.0)
        self.assertEqual(result["annoy_distance"], 0.0)

    def test_rejects_non_positive_k(self):
        with self.assertRaisesRegex(ValueError, "k must be at least 1"):
            search_index(np.eye(2, dtype=np.float32), chunks(2), [1.0, 0.0], k=0)


class ApiTests(unittest.TestCase):
    def test_accepts_makefile_port_argument(self):
        self.assertEqual(rag_api.parse_args(["--port", "8765"]).port, 8765)

    def test_server_uses_makefile_port_argument(self):
        server = mock.Mock()
        with (
            mock.patch.object(rag_api.os.path, "exists", return_value=True),
            mock.patch.object(rag_api, "load"),
            mock.patch.object(
                rag_api, "ThreadingHTTPServer", return_value=server
            ) as server_class,
        ):
            rag_api.main(["--port", "8765"])

        server_class.assert_called_once_with(("127.0.0.1", 8765), rag_api.Handler)
        server.serve_forever.assert_called_once_with()

    def test_response_reports_result_count(self):
        results = [{"chunk_id": 1}, {"chunk_id": 2}]
        with mock.patch.object(rag_api, "search", return_value=results):
            response = rag_api.search_response("query")

        self.assertEqual(response["count"], 2)
        self.assertEqual(response["results"], results)


class StatusTests(unittest.TestCase):
    def test_reports_search_backend_and_api(self):
        with tempfile.TemporaryDirectory() as directory:
            corpus = Path(directory)
            (corpus / "index").mkdir()
            (corpus / "index" / "config.json").write_text(
                json.dumps({"n_chunks": 3, "n_files": 2}), encoding="utf-8"
            )
            env = os.environ.copy()
            env["COURSE_CORPUS_ROOT"] = str(corpus)

            result = subprocess.run(
                [sys.executable, str(TOOLS / "status.py")],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

        self.assertEqual(result.returncode, 0)
        self.assertIn("backend: exact-cosine", result.stdout)
        self.assertIn("RAG-API скрипт: есть", result.stdout)


if __name__ == "__main__":
    unittest.main()
