import re
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
        r"([А-ЯЁ][а-яё]+\s+государственн\w+\s+(?:техническ\w+|университет\w*))",
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
        r"№\s*([\dА-Яа-я\-\./]+)",
    ],
    "issue_date": [
        r"(\d{2}\.\d{2}\.\d{4})\s+г\.\s+№",
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


def extract_study_period(text: str) -> str:
    """Собирает период из даты зачисления + даты завершения."""
    start = end = None

    # дата зачисления — несколько вариантов OCR
    for pattern in (
        r"зачислен\w*[^\d]{0,30}(\d{2}\.\d{2}\.\d{4})",
        r"дата\s+зачислени\w*[^\d]{0,10}(\d{2}\.\d{2}\.\d{4})",
        r"дивслени\w*[^\d]{0,10}(\d{2}\.\d{2}\.\d{4})",       # OCR: «дивсления»
        r"дислени\w*[^\d]{0,10}(\d{2}\.\d{2}\.\d{4})",
        r"исчислени\w*[^\d]{0,10}(\d{2}\.\d{2}\.\d{4})",
    ):
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            start = m.group(1)
            break

    # дата завершения
    for pattern in (
        r"завершени\w*\s+обучени\w*[^\d]{0,20}(\d{2}\.\d{2}\.\d{4})",
        r"(\d{2}\.\d{2}\.\d{4})\s*[Гг]\.?\s*$",
    ):
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            end = m.group(1)
            break

    if start and end:
        return f"{start} – {end}"
    return start or end or "не найдено"


def extract_program(text: str) -> str:
    """Код специальности + название после него."""
    m = re.search(r"(\d{2}\.\d{2}\.\d{2})\s+([А-ЯЁ][а-яё][^\n]{3,120})", text, re.MULTILINE)
    if m:
        return f"{m.group(1)} {m.group(2).strip().rstrip('.')}"
    m = re.search(r"(\d{2}\.\d{2}\.\d{2})", text)
    return m.group(1) if m else "не найдено"


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
            value = extract_study_period(text)
        elif field == "program":
            value = extract_program(text)

        fields[field] = value or "не найдено"

    return fields