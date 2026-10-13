"""Carry visual evidence to fields without inferring signatures from OCR words."""

import re
import unicodedata

from ml2.ocr_fixes import apply_ocr_fixes


def apply_visual_features(fields: dict, evidence) -> None:
    ready = isinstance(evidence, dict) and evidence.get("status") == "ready"
    for name in ("signature", "stamp"):
        if name in fields:
            value = evidence.get(name) if ready else None
            fields[name] = value if type(value) is bool else None


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", apply_ocr_fixes(text)).casefold().split())


def link_coordinates(coordinates, fields: dict) -> list[dict]:
    if not isinstance(coordinates, list):
        return []
    linked = []
    for item in coordinates:
        if not isinstance(item, dict):
            continue
        if item.get("source") not in {"spotting", "tesseract"}:
            linked.append(item)
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue
        normalized = normalize(text)
        names = []
        for name, value in fields.items():
            if not isinstance(value, str) or value == "не найдено":
                continue
            target = normalize(value)
            # Short tokens such as a course number are ambiguous on a whole page.
            if len(target) >= 4 and re.search(r"(?<!\w)" + re.escape(target) + r"(?!\w)", normalized):
                names.append(name)
        linked.extend({**item, "field": name} for name in names or [None])
    return linked
