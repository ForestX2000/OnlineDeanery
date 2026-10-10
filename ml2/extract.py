import re
from typing import Any

# имена полей совпадают с rules.json в backend/
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

RE_FIO = re.compile(r"\b[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2}\b")
RE_DATE = re.compile(r"\b\d{2}[.\-/]\d{2}[.\-/]\d{4}\b")
RE_NUMBER = re.compile(r"№\s*\d+")
RE_GROUP = re.compile(r"\b[А-ЯЁ]{2,4}-\d{2,4}\b")

# маркеры для поиска значения после ключевого слова
MARKERS: dict[str, list[str]] = {
    "student_name": ["фио", "студент", "обучающийся", "ф.и.о"],
    "university": ["вуз", "университет", "институт", "академия"],
    "program": ["направление", "специальность"],
    "study_form": ["форма обучения", "очная", "заочная"],
    "study_period": ["период обучения", "срок обучения", "годы обучения"],
    "document_number": ["номер", "№"],
    "issue_date": ["дата выдачи"],
    "group": ["группа"],
    "course": ["курс"],
    "reason": ["причина"],
    "start_date": ["дата начала"],
    "end_date": ["дата окончания"],
    "application_date": ["дата заявления"],
    "signature": ["подпись"],
    "stamp": ["печать", "м.п."],
    "organization": ["организация", "предприятие"],
    "internship_period": ["сроки практики", "срок"],
    "supervisor": ["руководитель"],
    "grade": ["оценка"],
}


# ищет значение после маркера в пределах window символов
def _find_by_marker(text: str, marker: str, window: int = 60) -> str | None:
    low = text.lower()
    idx = low.find(marker.lower())
    if idx == -1:
        return None
    tail = text[idx + len(marker): idx + len(marker) + window]
    tail = tail.split("\n")[0].strip(" :—-")
    return tail or None


# извлекает все поля документа; отсутствующие помечает "не найдено"
def extract_fields(text: str, doc_type: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    wanted = FIELDS_BY_TYPE.get(doc_type, [])

    for field in wanted:
        value: str | None = None

        for marker in MARKERS.get(field, []):
            value = _find_by_marker(text, marker)
            if value:
                break

        if not value:
            if field == "student_name":
                m = RE_FIO.search(text)
                value = m.group(0) if m else None
            elif field in ("issue_date", "start_date", "end_date", "application_date"):
                m = RE_DATE.search(text)
                value = m.group(0) if m else None
            elif field == "group":
                m = RE_GROUP.search(text)
                value = m.group(0) if m else None
            elif field == "document_number":
                m = RE_NUMBER.search(text)
                value = m.group(0) if m else None

        fields[field] = value or "не найдено"

    return fields