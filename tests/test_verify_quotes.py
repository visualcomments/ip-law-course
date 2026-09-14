import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"


def write_verifier_fixture(tmp_path, cited_chunk, available_source=True):
    repo = tmp_path / "repo"
    texts = tmp_path / "corpus" / "txt"
    index = tmp_path / "corpus" / "index"
    (repo / "lectures").mkdir(parents=True)
    (repo / "verification").mkdir()
    texts.mkdir(parents=True)
    index.mkdir(parents=True)

    quote = "Это достаточно длинная цитата для проверки координат"
    (repo / "lectures" / "01_test.md").write_text(
        f"> **Цитата:** «{quote}»\n"
        f"> **Источник:** `txt/source.txt` · фрагмент #{cited_chunk}\n",
        encoding="utf-8",
    )
    report = repo / "verification" / "REPORT.md"
    report.write_text("previous report\n", encoding="utf-8")
    if available_source:
        (texts / "source.txt").write_text(quote, encoding="utf-8")
    else:
        (texts / "unrelated.txt").write_text("другой текст", encoding="utf-8")
    (index / "chunks.jsonl").write_text(
        json.dumps(
            {"file": "source.txt", "chunk_id": 8, "text": quote},
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return repo, texts, index, report


def run_verifier(repo, texts, index):
    env = os.environ.copy()
    env.update(
        {
            "COURSE_REPO_DIR": str(repo),
            "COURSE_TXT_DIR": str(texts),
            "COURSE_INDEX_DIR": str(index),
        }
    )
    return subprocess.run(
        [sys.executable, str(TOOLS / "verify_quotes.py")],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


class VerifierTests(unittest.TestCase):
    def test_accepts_matching_chunk_coordinate(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, texts, index, report = write_verifier_fixture(
                Path(directory), cited_chunk=8
            )

            result = run_verifier(repo, texts, index)

            self.assertEqual(result.returncode, 0)
            self.assertIn("неудач: **0**", report.read_text(encoding="utf-8"))

    def test_rejects_wrong_chunk_coordinate(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, texts, index, report = write_verifier_fixture(
                Path(directory), cited_chunk=7
            )

            result = run_verifier(repo, texts, index)

            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "FAIL: указан #7, найден #8", report.read_text(encoding="utf-8")
            )

    def test_preserves_report_for_incomplete_corpus(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, texts, index, report = write_verifier_fixture(
                Path(directory), cited_chunk=8, available_source=False
            )

            result = run_verifier(repo, texts, index)

            self.assertEqual(result.returncode, 2)
            self.assertEqual(report.read_text(encoding="utf-8"), "previous report\n")

    def test_preserves_report_for_incomplete_index(self):
        with tempfile.TemporaryDirectory() as directory:
            repo, texts, index, report = write_verifier_fixture(
                Path(directory), cited_chunk=8
            )
            (index / "chunks.jsonl").unlink()

            result = run_verifier(repo, texts, index)

            self.assertEqual(result.returncode, 2)
            self.assertEqual(report.read_text(encoding="utf-8"), "previous report\n")


if __name__ == "__main__":
    unittest.main()
