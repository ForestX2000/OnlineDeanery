"""Measure OCR errors against a manually checked UTF-8 reference.

Run from the repository root (no models or datasets are downloaded)::

    python -m tools.evaluate_ocr --reference reference.txt --prediction result.txt
    python -m tools.evaluate_ocr --reference reference.txt --file scan.png --output baseline.json
    python -m tools.evaluate_ocr --reference reference.txt --file scan.png --compare baseline.json

CER and WER are Levenshtein distance divided by reference length. They can
exceed 1 when the prediction contains many insertions. Only NFKC and whitespace
normalization are applied: case, punctuation, and Russian е/ё remain distinct.
Reports include the recognized text; store them locally with the source document.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import mimetypes
from pathlib import Path
import sys
import time
from typing import Any, Sequence
import unicodedata


SCHEMA_VERSION = 1
NORMALIZATION = "nfkc-collapse-whitespace-v1"
DEFAULT_URL = "http://localhost:8001/ocr"


def normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).split())


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def edit_distance(reference: Sequence[str], prediction: Sequence[str]) -> int:
    """Levenshtein distance using one row of memory, with unit edit costs."""
    if reference == prediction:
        return 0
    # Shared text cannot contribute to an optimal edit, and trimming it helps
    # when evaluating long documents with only a small incorrect region.
    start = 0
    end_reference, end_prediction = len(reference), len(prediction)
    while start < min(end_reference, end_prediction) and reference[start] == prediction[start]:
        start += 1
    while (
        end_reference > start
        and end_prediction > start
        and reference[end_reference - 1] == prediction[end_prediction - 1]
    ):
        end_reference -= 1
        end_prediction -= 1
    reference = reference[start:end_reference]
    prediction = prediction[start:end_prediction]
    if len(reference) > len(prediction):
        reference, prediction = prediction, reference
    if not reference:
        return len(prediction)
    previous = list(range(len(reference) + 1))
    for row, predicted in enumerate(prediction, 1):
        current = [row]
        for column, expected in enumerate(reference, 1):
            current.append(min(
                previous[column] + 1,
                current[column - 1] + 1,
                previous[column - 1] + (expected != predicted),
            ))
        previous = current
    return previous[-1]


def calculate_metrics(reference: str, prediction: str) -> dict[str, int | float]:
    reference = normalize_text(reference)
    prediction = normalize_text(prediction)
    if not reference:
        raise ValueError("Reference must contain non-whitespace text.")
    reference_words, prediction_words = reference.split(), prediction.split()
    character_edits = edit_distance(reference, prediction)
    word_edits = edit_distance(reference_words, prediction_words)
    return {
        "cer": character_edits / len(reference),
        "wer": word_edits / len(reference_words),
        "character_edits": character_edits,
        "word_edits": word_edits,
        "reference_characters": len(reference),
        "reference_words": len(reference_words),
        "prediction_characters": len(prediction),
        "prediction_words": len(prediction_words),
    }


def create_report(
    reference: str,
    prediction: str,
    *,
    mode: str = "offline",
    endpoint: str | None = None,
    input_bytes: bytes | None = None,
    duration_seconds: float = 0.0,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "normalization": NORMALIZATION,
        "mode": mode,
        "endpoint": endpoint,
        "duration_seconds": round(duration_seconds, 6),
        "reference_sha256": sha256(normalize_text(reference).encode("utf-8")),
        "input_sha256": sha256(input_bytes) if input_bytes is not None else None,
        "prediction_sha256": sha256(normalize_text(prediction).encode("utf-8")),
        "text": prediction,
        "metrics": calculate_metrics(reference, prediction),
    }


def compare_reports(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, float]:
    """Reject comparisons that do not describe the same evaluation sample."""
    if not isinstance(baseline, dict):
        raise ValueError("Baseline report must be a JSON object.")
    for key in ("schema_version", "normalization", "reference_sha256", "input_sha256"):
        if key not in baseline or baseline[key] != current[key]:
            raise ValueError(f"Cannot compare reports: {key} differs or is missing.")
    baseline_metrics = baseline.get("metrics")
    if not isinstance(baseline_metrics, dict):
        raise ValueError("Baseline report is missing metrics.")
    comparison = {}
    for metric in ("cer", "wer"):
        value = baseline_metrics.get(metric)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"Baseline report has an invalid {metric}.")
        comparison[f"baseline_{metric}"] = value
        # Negative deltas mean fewer errors. These are absolute rate changes,
        # not relative percentages (which are undefined for a perfect baseline).
        comparison[f"{metric}_delta"] = current["metrics"][metric] - value
    return comparison


def _assert_complete_response(value: Any) -> None:
    """Notice explicit incomplete-output metadata, including page diagnostics."""
    if isinstance(value, dict):
        if (
            value.get("finish_reason") in ("length", "max_tokens", "content_filter")
            or value.get("truncated") is True
            or value.get("incomplete") is True
            or value.get("complete") is False
            or value.get("status") in ("error", "failed", "incomplete", "truncated")
            or value.get("error")
            or value.get("errors")
        ):
            raise ValueError("OCR service reported an error or incomplete output; no score was saved.")
        for child in value.values():
            _assert_complete_response(child)
    elif isinstance(value, list):
        for child in value:
            _assert_complete_response(child)


def recognize_file(path: Path, content: bytes, url: str, timeout: float) -> str:
    import requests

    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    try:
        response = requests.post(
            url,
            files={"file": (path.name, content, content_type)},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise ValueError(f"OCR HTTP request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("OCR service response must be a JSON object.")
    _assert_complete_response(payload)
    text = payload.get("text")
    if not isinstance(text, str) or not normalize_text(text):
        raise ValueError("OCR service returned no recognized text; no score was saved.")
    return text


def _positive_timeout(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("timeout must be a positive finite number")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reference", required=True, type=Path, help="Manually checked UTF-8 transcription")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--prediction", type=Path, help="Existing UTF-8 OCR text (offline)")
    source.add_argument("--file", type=Path, help="Image or PDF to submit to the local OCR service")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"OCR service URL (default: {DEFAULT_URL})")
    parser.add_argument("--timeout", type=_positive_timeout, default=600.0, help="HTTP timeout in seconds (default: 600)")
    parser.add_argument("--output", type=Path, help="Write the complete JSON report to this file")
    parser.add_argument("--compare", type=Path, help="Compare CER/WER with a saved report for the same sample")
    args = parser.parse_args(argv)

    try:
        if args.output and args.output.resolve() in {
            path.resolve() for path in (args.reference, args.prediction, args.file, args.compare) if path is not None
        }:
            raise ValueError("Output must not overwrite a source file or baseline report.")
        reference = args.reference.read_text(encoding="utf-8-sig")
        if not normalize_text(reference):
            raise ValueError("Reference must contain non-whitespace text.")
        baseline = json.loads(args.compare.read_text(encoding="utf-8-sig")) if args.compare else None
        started = time.perf_counter()
        input_bytes = None
        if args.prediction:
            prediction = args.prediction.read_text(encoding="utf-8-sig")
            mode, endpoint = "offline", None
        else:
            input_bytes = args.file.read_bytes()
            if not input_bytes:
                raise ValueError("Input document is empty.")
            # Validate sample identity before making an unnecessary HTTP call.
            if args.compare:
                identity = create_report(reference, "", mode="http", endpoint=args.url, input_bytes=input_bytes)
                compare_reports(identity, baseline)
            prediction = recognize_file(args.file, input_bytes, args.url, args.timeout)
            mode, endpoint = "http", args.url
        report = create_report(
            reference, prediction, mode=mode, endpoint=endpoint,
            input_bytes=input_bytes, duration_seconds=time.perf_counter() - started,
        )
        if args.compare:
            report["comparison"] = compare_reports(report, baseline)
        rendered = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
            print(f"Report saved to {args.output}; CER={report['metrics']['cer']:.4f}, WER={report['metrics']['wer']:.4f}")
        else:
            print(rendered, end="")
        return 0
    except (OSError, ValueError, ImportError) as exc:
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
