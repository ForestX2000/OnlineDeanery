"""Carry visual evidence to fields without inferring signatures from OCR words."""

import re
import unicodedata
from difflib import SequenceMatcher

from ml2.ocr_fixes import apply_ocr_fixes


def apply_visual_features(fields: dict, evidence) -> None:
    ready = isinstance(evidence, dict) and evidence.get("status") == "ready"
    for name in ("signature", "stamp"):
        if name in fields:
            value = evidence.get(name) if ready else None
            fields[name] = value if type(value) is bool else None


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", apply_ocr_fixes(text)).casefold().split())


def field_match_score(name: str, value: str, text: str) -> float:
    """Score whether one OCR line contains an extracted field value."""
    target = normalize(value)
    candidate = normalize(text)
    if len(target) < 4 or not candidate:
        return 0.0
    if target in candidate:
        return 1.0

    target_digits = re.sub(r"\D", "", target)
    candidate_digits = re.sub(r"\D", "", candidate)
    if len(target_digits) >= 6 and target_digits in candidate_digits:
        return 1.0
    if name in {"study_period", "internship_period"}:
        dates = re.findall(r"\d{2}\.\d{2}\.\d{4}", target)
        matching_dates = [date for date in dates if re.sub(r"\D", "", date) in candidate_digits]
        if matching_dates:
            return len(matching_dates) / len(dates)

    target_tokens = [token for token in re.findall(r"[a-zа-яё0-9]+", target) if len(token) >= 3]
    candidate_tokens = [token for token in re.findall(r"[a-zа-яё0-9]+", candidate) if len(token) >= 3]
    if target_tokens and candidate_tokens:
        matched = 0
        for token in target_tokens:
            best = max(SequenceMatcher(None, token, candidate_token).ratio()
                       for candidate_token in candidate_tokens)
            if best >= 0.78:
                matched += 1
        coverage = matched / len(target_tokens)
        minimum_coverage = 0.6 if name in {"university", "program"} else 0.75
        if coverage >= minimum_coverage:
            return coverage

    compact_target = re.sub(r"\W", "", target)
    compact_candidate = re.sub(r"\W", "", candidate)
    return SequenceMatcher(None, compact_target, compact_candidate).ratio()


def link_coordinates(coordinates, fields: dict) -> list[dict]:
    if not isinstance(coordinates, list):
        return []
    text_boxes = []
    other_boxes = []
    for index, item in enumerate(coordinates):
        if not isinstance(item, dict):
            continue
        if item.get("source") not in {"spotting", "tesseract"}:
            other_boxes.append(item)
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue

        for name, value in fields.items():
            if not isinstance(value, str) or value == "не найдено":
                continue
            score = field_match_score(name, value, text)
            if score < 0.72:
                continue
            text_boxes.append((score, index, name, value, item))

    best_by_field = {}
    for match in text_boxes:
        score, index, name, value, item = match
        current = best_by_field.get(name)
        if current is None or score > current[0]:
            best_by_field[name] = match

    linked_text = [
        {**item, "field": name, "text": value}
        for score, index, name, value, item in sorted(best_by_field.values(), key=lambda m: m[1])
    ]
    return linked_text + other_boxes
