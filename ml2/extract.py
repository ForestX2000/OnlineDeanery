import re
from datetime import date
from typing import Any

FIELDS_BY_TYPE: dict[str, list[str]] = {
    "study_certificate": [
        "student_name", "university", "program", "study_form",
        "study_period", "document_number", "issue_date",
        "signature", "stamp",
    ],
    "academic_leave": [
        "student_name", "group", "course", "reason",
        "start_date", "end_date", "application_date", "signature",
    ],
    "internship_certificate": [
        "student_name", "organization", "internship_period",
        "supervisor", "grade", "document_number", "issue_date",
        "signature", "stamp",
    ],
}

PATTERNS: dict[str, list[str]] = {
    "student_name": [
        r"([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)\s*\(\d{2}\.\d{2}\.\d{4}",
        r"фио[:\s]+([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})",
    ],
    "university": [
        r"«([^»]{5,120}?(?:университет|институт|академия|колледж)[^»]*?)»",
        r"([А-ЯЁ][а-яё]+\s+государственн\w+\s+(?:техническ\w+\s+)?(?:университет\w*|колледж\w*)?)",
        r"([А-ЯЁ]{2,8}(?:ГУ|ГТУ|ГАУ|ПГУ|ТУ|ИУ|АСУ))\b",
    ],
    "program": [
        r"(\d{2}\.\d{2}\.\d{2})\s+([А-ЯЁ][а-яё][^\n]{3,120})",
    ],
    "study_form": [
        r"\b(очн\w*|заочн\w*|очно-заочн\w*)\s+форм\w*\s+обучени\w*",
        r"по\s+(очн\w+|заочн\w+)\s+форм",
        r"\b(очн\w+|заочн\w+)\b",
    ],
    "study_period": [
        # handled отдельно в extract_study_period
    ],
    "document_number": [
        r"\d{2}\.\d{2}\.\d{4}\s*(?:г\.?\s*)?(?:№|N[oо]?\.?|#)\s*([\dА-Яа-яЁё\-\./]+)",
        r"№\s*([\dА-Яа-я\-\./]+)",
    ],
    "issue_date": [
        r"(?<!\d)(\d{2}\.\d{2}\.\d{4})\s*(?:г\.?\s*)?(?:№|N[oо]?\.?|#)",
        r"дата\s+выдачи[:\s]*(\d{2}\.\d{2}\.\d{4})",
    ],
    "group": [
        r"групп\w*[:\s]+([А-ЯЁ]{2,4}[-–]?\d{2,4}[А-ЯЁа-яё]*)",
        r"\b([А-ЯЁ]{2,4}[-–]\d{2,4}[А-ЯЁа-яё]?)\b",
    ],
    "course": [
        r"на\s+(\d)\s*(?:-?м|м)?\s*курс",
        r"(\d)\s*(?:-?й|й)?\s*курс",
    ],
    "reason": [r"причин\w*[:\s]+([^\n]{3,200})"],
    "start_date": [
        r"дата\s+начала[:\s]*(\d{2}\.\d{2}\.\d{4})",
        r"дата\s+начала[^\d\n]{0,40}(\d{2}\.\d{2}\.\d{4})",
    ],
    "end_date": [
        r"дата\s+окончания[:\s]*(\d{2}\.\d{2}\.\d{4})",
        r"дата\s+окончания[^\d\n]{0,40}(\d{2}\.\d{2}\.\d{4})",
    ],
    "application_date": [r"дата\s+заявления[:\s]*(\d{2}\.\d{2}\.\d{4})"],
    "organization": [r"«([^»]{5,100}?)»"],
    "internship_period": [
        r"(с\s+\d{2}\.\d{2}\.\d{4}\s+по\s+\d{2}\.\d{2}\.\d{4})",
        r"с\s+(\d{2}\.\d{2}\.\d{4})\s+по\s+\d{2}\.\d{2}\.\d{4}",
    ],
    "supervisor": [r"руководител\w*[:\s]+([А-ЯЁ][^\n\.]{2,100})"],
    "grade": [r"оценк\w*[:\s]+([А-ЯЁа-яё][^\n\.]{1,50})"],
}


def extract_field(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            value = m.group(1).strip().rstrip(".,;:")
            if value:
                return value
    return None


def normalize_study_form(value: str | None) -> str:
    """«очной» → «очная», «заочной» → «заочная»."""
    if not value:
        return "не найдено"
    v = value.lower()
    if "очно-заочн" in v:
        return "очно-заочная"
    if "заочн" in v:
        return "заочная"
    if "очн" in v:
        return "очная"
    return value


_DATE_TOKEN = r"(?<!\d)(?:\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{1,2}[./]\d{4}|\d{1,2}[./]\d{1,2}|\d{4})(?!\d)"


def _parse_date_token(value: str) -> tuple[str, str, date | None] | None:
    """Нормализует полную или частично распознанную дату без выдумывания её частей."""
    parts = re.split(r"[./]", value)
    try:
        if len(parts) == 3 and len(parts[2]) in {2, 4}:
            day, month, year = map(int, parts)
            if len(parts[2]) == 2:
                year += 2000 if year < 70 else 1900
            parsed = date(year, month, day)
            return parsed.strftime("%d.%m.%Y"), "day", parsed
        if len(parts) == 2 and len(parts[1]) == 4:
            month, year = map(int, parts)
            if not 1 <= month <= 12 or not 1900 <= year <= 2100:
                return None
            return f"{month:02d}.{year:04d}", "month", None
        if len(parts) == 2:
            day, month = map(int, parts)
            date(2000, month, day)
            return f"{day:02d}.{month:02d}", "day_month", None
        if len(parts) == 1:
            year = int(parts[0])
            if 1900 <= year <= 2100:
                return f"{year:04d}", "year", None
    except ValueError:
        return None
    return None


def _date_after_label(text: str, label: str) -> tuple[str, str, date | None] | None:
    for match in re.finditer(label, text, re.IGNORECASE):
        # Между подписью поля и его датой OCR часто оставляет номер приказа,
        # поэтому нельзя ограничивать поиск первым числом.
        tail = text[match.end():match.end() + 140].splitlines()[0]
        for candidate in re.finditer(_DATE_TOKEN, tail):
            parsed = _parse_date_token(candidate.group(0))
            if parsed:
                return parsed
    return None


def _study_period_details(text: str) -> tuple[str, str | None]:
    """Извлекает подтверждённые границы периода и объясняет восстановление даты."""
    notes: list[str] = []
    enrollment = (
        _date_after_label(text, r"\bдата\s+(?:зачислени\w*|дивслени\w*|дислени\w*|исчислени\w*)")
        or _date_after_label(text, r"\bзачислен\w*\s+(?:с|на|в)\b")
        or _date_after_label(text, r"\b(?:зачислени\w*|дивслени\w*|дислени\w*|исчислени\w*)")
    )

    start = end = None
    range_pattern = rf"\bс\s*({_DATE_TOKEN})[^\n]{{0,50}}?\b(?:по|до)\s*({_DATE_TOKEN})"
    for match in re.finditer(range_pattern, text, re.IGNORECASE):
        candidate_start = _parse_date_token(match.group(1))
        candidate_end = _parse_date_token(match.group(2))
        if candidate_start and candidate_end:
            start, end = candidate_start, candidate_end
            break

    if start is None:
        start = _date_after_label(text, r"\b(?:дата\s+)?начала\s+обучени\w*")
    if end is None:
        end = _date_after_label(text, r"\b(?:дата\s+)?(?:завершени\w*|окончани\w*)\s+обучени\w*")

    if enrollment and (start is None or start[1] != "day"):
        start = enrollment
        notes.append("Начало периода взято из даты зачисления.")
        if enrollment[1] != "day":
            notes.append(f"Дата зачисления распознана частично ({enrollment[0]}).")

    if start and end and start[2] and end[2] and end[2] < start[2]:
        end = None
        notes.append("Дата окончания раньше даты зачисления и не включена в период.")

    if end and end[1] != "day":
        notes.append(f"Дата окончания распознана частично ({end[0]}); недостающие части не подставлялись.")
    elif start and not end:
        notes.append("Полную дату окончания обучения не удалось распознать.")
    if start and start[1] != "day" and not enrollment:
        notes.append(f"Дата начала распознана частично ({start[0]}).")

    value = " – ".join(item[0] for item in (start, end) if item)
    return value or "не найдено", " ".join(notes) or None


def extract_study_period(text: str) -> str:
    """Собирает период обучения, используя дату зачисления как достоверное начало."""
    return _study_period_details(text)[0]


def extract_program(text: str) -> str:
    """Код специальности + название после него."""
    matches = re.finditer(
        r"(?<!\d)(\d{2}\.\d{2}\.\d{2})(?!\.\d{2})\s+([А-ЯЁа-яё][^\n]{3,120})",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    for match in matches:
        title = match.group(2).strip()
        # OCR sometimes sees a short date (e.g. 10.06.20 г.) as a code.
        if re.match(r"(?i)^г(?:од)?(?:\.|\s|$)", title):
            continue
        return f"{match.group(1)} {title.rstrip('.')}"
    return "не найдено"


def extract_fields(text: str, doc_type: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    wanted = FIELDS_BY_TYPE.get(doc_type, [])

    for field in wanted:
        if field in ("signature", "stamp"):
            fields[field] = "не найдено"
            continue

        value = extract_field(text, PATTERNS.get(field, []))

        # спец-нормализация
        if field == "study_form":
            value = normalize_study_form(value)
        elif field == "study_period":
            value, note = _study_period_details(text)
            if note:
                fields["study_period_note"] = note
        elif field == "program":
            value = extract_program(text)

        fields[field] = value or "не найдено"

    return fields
