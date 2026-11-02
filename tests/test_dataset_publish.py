# SPDX-License-Identifier: GPL-3.0-or-later
"""Проверки сборки датасета на временных submissions, без сети."""

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
PUBLISH = ROOT / "assignments/00-first-contribution/dataset-schema/publish.py"
SPEC = importlib.util.spec_from_file_location("dataset_publish", PUBLISH)
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


class DatasetPublishTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.submissions = self.root / "submissions"
        self.submissions.mkdir()
        self.out = self.root / "dataset"
        self.source = self.root / "source.txt"
        self.source.write_text("Тестовый текст источника.", encoding="utf-8")

    def record(self, record_id, *, license="official-document", title="Поправка"):
        return {
            "schema": 1,
            "record_id": record_id,
            "profile": "amendment",
            "title_ru": title,
            "norm": {
                "source_law": "ГК РФ",
                "article": "ст.1252",
                "norm_id": "гк-рф/ст.1252",
            },
            "amending_doc": "Тестовый акт",
            "predicate": "изменена",
            "change_ru": "Тестовое изменение нормы.",
            "source": {
                "file": str(self.source),
                "coord": "строка 1",
                "doc_type": "official_document",
                "license": license,
            },
            "provenance": {
                "extracted_by": "test",
                "extracted_at": "2026-01-01",
                "method": "script",
            },
            "review": {"status": "proposed"},
            "evidence_quote": "Тестовый текст источника.",
        }

    def write_submission(self, name, *rows):
        path = self.submissions / name
        path.write_text(
            "".join(
                json.dumps(row, ensure_ascii=False) + "\n" if row else "\n"
                for row in rows
            ),
            encoding="utf-8",
        )
        return path

    def arguments(self):
        return [
            str(PUBLISH),
            "--submissions-dir",
            str(self.submissions),
            "--out-dir",
            str(self.out),
            "--assets-root",
            str(self.root),
        ]

    def run_publisher(self):
        return subprocess.run(
            [sys.executable, *self.arguments(), "--dry-run"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )

    def test_rejects_identical_and_conflicting_duplicates_with_locations(self):
        for same_file in (True, False):
            for identical in (True, False):
                with self.subTest(same_file=same_file, identical=identical):
                    first = self.record("test.duplicate")
                    second = self.record(
                        "test.duplicate",
                        title=first["title_ru"] if identical else "Другая поправка",
                    )
                    first_path = self.write_submission("a.jsonl", None, first)
                    if same_file:
                        self.write_submission("a.jsonl", None, first, None, second)
                        second_path, second_line = first_path, 4
                    else:
                        second_path = self.write_submission(
                            "b.jsonl", None, None, second
                        )
                        second_line = 3

                    result = self.run_publisher()

                    self.assertEqual(
                        result.returncode, 1, result.stdout + result.stderr
                    )
                    self.assertIn(
                        "ОШИБКА: повтор record_id='test.duplicate'", result.stdout
                    )
                    self.assertIn(
                        f"{first_path}:2 и {second_path}:{second_line}", result.stdout
                    )
                    self.assertFalse(self.out.exists())
                    for path in self.submissions.glob("*.jsonl"):
                        path.unlink()

    def test_reports_every_duplicate(self):
        first = self.write_submission("a.jsonl", self.record("test.duplicate"))
        second = self.write_submission("b.jsonl", self.record("test.duplicate"))
        third = self.write_submission("c.jsonl", self.record("test.duplicate"))

        result = self.run_publisher()

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(f"{first}:1 и {second}:1", result.stdout)
        self.assertIn(f"{first}:1 и {third}:1", result.stdout)
        self.assertIn("повторов record_id: 2", result.stdout)

    def test_rejects_duplicates_before_license_filtering(self):
        self.write_submission(
            "a.jsonl", self.record("test.duplicate", license="cite-only")
        )
        self.write_submission("b.jsonl", self.record("test.duplicate"))

        result = self.run_publisher()

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("ОШИБКА: повтор record_id=", result.stdout)
        self.assertFalse(self.out.exists())

    def test_duplicate_preserves_output_and_skips_remote_access(self):
        self.write_submission("a.jsonl", self.record("test.duplicate"))
        self.write_submission("b.jsonl", self.record("test.duplicate"))
        self.out.mkdir()
        previous = {
            "records.jsonl": b"previous records\n",
            "README.md": b"previous card\n",
        }
        for name, content in previous.items():
            (self.out / name).write_bytes(content)

        with (
            mock.patch.object(
                sys, "argv", self.arguments() + ["--repo-id", "test/dataset"]
            ),
            mock.patch.dict("os.environ", {"HF_TOKEN": "unused-test-token"}),
            mock.patch.object(publisher, "load_existing") as load_existing,
            mock.patch.dict(sys.modules, {"huggingface_hub": mock.Mock()}) as modules,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(publisher.main(), 1)
            load_existing.assert_not_called()
            modules["huggingface_hub"].HfApi.assert_not_called()

        self.assertEqual({p.name for p in self.out.iterdir()}, set(previous))
        for name, content in previous.items():
            self.assertEqual((self.out / name).read_bytes(), content)

    def test_unique_records_keep_license_filtering(self):
        first = self.record("test.first")
        second = self.record("test.second")
        self.write_submission(
            "a.jsonl", first, self.record("test.excluded", license="cite-only")
        )
        self.write_submission("b.jsonl", second)

        result = self.run_publisher()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        records = [
            json.loads(line)
            for line in (self.out / "records.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        self.assertEqual(records, [first, second])
        self.assertTrue((self.out / "README.md").is_file())

    def test_submission_can_update_a_published_record(self):
        updated = self.record("test.existing", title="Исправленная поправка")
        previous = self.record("test.existing", title="Прежняя поправка")
        retained = self.record("test.retained")
        self.write_submission("a.jsonl", updated)
        api = mock.Mock()
        hub = mock.Mock()
        hub.HfApi.return_value = api

        with (
            mock.patch.object(
                sys, "argv", self.arguments() + ["--repo-id", "test/dataset"]
            ),
            mock.patch.dict("os.environ", {"HF_TOKEN": "unused-test-token"}),
            mock.patch.object(
                publisher,
                "load_existing",
                return_value={
                    previous["record_id"]: previous,
                    retained["record_id"]: retained,
                },
            ),
            mock.patch.dict(sys.modules, {"huggingface_hub": hub}),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(publisher.main(), 0)

        records = [
            json.loads(line)
            for line in (self.out / "records.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        self.assertEqual(records, [updated, retained])
        api.upload_folder.assert_called_once()


if __name__ == "__main__":
    unittest.main()
