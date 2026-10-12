"""Regression checks for reproducible OCR quality measurements."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools.evaluate_ocr import (
    calculate_metrics,
    compare_reports,
    create_report,
    edit_distance,
    main,
    normalize_text,
    recognize_file,
)


class MetricTests(unittest.TestCase):
    def test_known_character_and_word_edits(self):
        self.assertEqual(edit_distance("kitten", "sitting"), 3)
        self.assertEqual(edit_distance("prefix abc suffix", "prefix axc suffix"), 1)
        result = calculate_metrics("кот дом", "код дом")
        self.assertEqual(result["character_edits"], 1)
        self.assertAlmostEqual(result["cer"], 1 / 7)
        self.assertEqual(result["wer"], 0.5)

    def test_normalizes_only_nfkc_and_whitespace(self):
        self.assertEqual(normalize_text("  A\u0308\tＦＩＯ\n  ё  "), "Ä FIO ё")
        self.assertEqual(calculate_metrics("a b", "a\n\tb")["cer"], 0)
        for expected, actual in (("ё", "е"), ("А", "а"), (".", ",")):
            with self.subTest(expected=expected):
                self.assertEqual(calculate_metrics(expected, actual)["cer"], 1)

    def test_empty_prediction_is_all_deletions(self):
        result = calculate_metrics("два слова", " \n")
        self.assertEqual(result["cer"], 1)
        self.assertEqual(result["wer"], 1)

    def test_insertions_can_exceed_one(self):
        self.assertEqual(calculate_metrics("a", "a b c")["wer"], 2)
        self.assertEqual(calculate_metrics("a", "abcd")["cer"], 3)

    def test_empty_reference_is_not_a_valid_sample(self):
        with self.assertRaises(ValueError):
            calculate_metrics("\t \n", "текст")


class ComparisonTests(unittest.TestCase):
    def test_normalized_identity_and_absolute_deltas(self):
        baseline = create_report("кот\nдом", "код дом", input_bytes=b"same image")
        current = create_report("кот дом", "кот дом", input_bytes=b"same image")
        result = compare_reports(current, baseline)
        self.assertAlmostEqual(result["cer_delta"], -1 / 7)
        self.assertEqual(result["wer_delta"], -0.5)

    def test_rejects_reference_and_document_mismatches(self):
        baseline = create_report("кот дом", "кот", input_bytes=b"first image")
        for current in (
            create_report("другой эталон", "кот", input_bytes=b"first image"),
            create_report("кот дом", "кот", input_bytes=b"different image"),
            create_report("кот дом", "кот"),
        ):
            with self.subTest(current=current), self.assertRaises(ValueError):
                compare_reports(current, baseline)

    def test_rejects_invalid_or_missing_baseline_metadata(self):
        current = create_report("кот", "кот")
        for baseline in (
            {},
            [],
            {**current, "normalization": "different"},
            {**current, "metrics": {"cer": float("nan"), "wer": 0}},
            {**current, "metrics": {"cer": True, "wer": 0}},
        ):
            with self.subTest(baseline=baseline), self.assertRaises(ValueError):
                compare_reports(current, baseline)


class EvaluationCliTests(unittest.TestCase):
    def test_offline_cli_writes_report_and_compares(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            reference, prediction = folder / "reference.txt", folder / "prediction.txt"
            baseline_path, output_path = folder / "baseline.json", folder / "current.json"
            reference.write_text("кот дом", encoding="utf-8")
            prediction.write_text("код дом", encoding="utf-8")
            common = ["--reference", str(reference), "--prediction", str(prediction)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(common + ["--output", str(baseline_path)]), 0)
                prediction.write_text("кот дом", encoding="utf-8")
                self.assertEqual(main(common + ["--output", str(output_path), "--compare", str(baseline_path)]), 0)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(report["mode"], "offline")
            self.assertIsNone(report["input_sha256"])
            self.assertIsNone(report["endpoint"])
            self.assertEqual(report["metrics"]["cer"], 0)
            self.assertLess(report["comparison"]["cer_delta"], 0)
            self.assertGreaterEqual(report["duration_seconds"], 0)

    def test_online_mismatch_prevents_http_and_does_not_write_report(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            reference, image = folder / "reference.txt", folder / "scan.png"
            baseline_path, output = folder / "baseline.json", folder / "output.json"
            reference.write_text("эталон", encoding="utf-8")
            image.write_bytes(b"new document")
            baseline_path.write_text(json.dumps(create_report("эталон", "текст", input_bytes=b"old document")), encoding="utf-8")
            with patch("tools.evaluate_ocr.recognize_file") as recognize, contextlib.redirect_stderr(io.StringIO()):
                code = main(["--reference", str(reference), "--file", str(image), "--compare", str(baseline_path), "--output", str(output)])
            self.assertEqual(code, 2)
            recognize.assert_not_called()
            self.assertFalse(output.exists())

    def test_refuses_to_overwrite_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            reference = Path(directory) / "reference.txt"
            reference.write_text("эталон", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                code = main(["--reference", str(reference), "--prediction", str(reference), "--output", str(reference)])
            self.assertEqual(code, 2)
            self.assertEqual(reference.read_text(encoding="utf-8"), "эталон")

    @patch("requests.post")
    def test_http_failure_and_blank_result_do_not_create_report(self, post):
        import requests
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            reference, image, output = folder / "reference.txt", folder / "scan.png", folder / "report.json"
            reference.write_text("эталон", encoding="utf-8")
            image.write_bytes(b"image")
            arguments = ["--reference", str(reference), "--file", str(image), "--output", str(output)]
            for response in (
                Mock(raise_for_status=Mock(side_effect=requests.HTTPError("502 truncated OCR"))),
                Mock(json=lambda: {"text": " "}),
                Mock(json=Mock(side_effect=ValueError("invalid JSON"))),
            ):
                with self.subTest(response=response), contextlib.redirect_stderr(io.StringIO()):
                    post.return_value = response
                    self.assertEqual(main(arguments), 2)
                    self.assertFalse(output.exists())


class HttpEvaluationTests(unittest.TestCase):
    @patch("requests.post")
    def test_uploads_exact_bytes_and_preserves_returned_text(self, post):
        post.return_value = Mock(json=lambda: {"text": "текст\n"})
        self.assertEqual(recognize_file(Path("scan.pdf"), b"pdf", "http://localhost/ocr", 30), "текст\n")
        self.assertEqual(post.call_args.kwargs["files"]["file"], ("scan.pdf", b"pdf", "application/pdf"))
        self.assertEqual(post.call_args.kwargs["timeout"], 30)
        post.return_value.raise_for_status.assert_called_once()

    @patch("requests.post")
    def test_rejects_empty_missing_and_explicitly_incomplete_text(self, post):
        for payload in (
            {}, {"text": None}, {"text": "  "}, [],
            {"text": "часть", "finish_reason": "length"},
            {"text": "часть", "pages": [{"truncated": True}]},
            {"text": "часть", "diagnostics": {"complete": False}},
            {"text": "часть", "error": "failure"},
        ):
            with self.subTest(payload=payload):
                post.return_value = Mock(json=lambda: payload)
                with self.assertRaises(ValueError):
                    recognize_file(Path("scan.png"), b"image", "http://localhost/ocr", 30)

    @patch("requests.post")
    def test_http_errors_are_not_scored(self, post):
        import requests
        post.return_value.raise_for_status.side_effect = requests.HTTPError("503 unavailable")
        with self.assertRaisesRegex(ValueError, "OCR HTTP request failed"):
            recognize_file(Path("scan.png"), b"image", "http://localhost/ocr", 30)
        post.return_value.json.assert_not_called()


if __name__ == "__main__":
    unittest.main()
