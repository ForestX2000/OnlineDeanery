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
        r"дан[ао]?\s+[_\s]*([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})",
        r"выдан[ао]?\s+([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})",
        r"что\s+([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)\s+действительно",
    ],
    "university": [
        r"«([^»]{5,120}?(?:университет|институт|академия|колледж)[^»]*?)»",
        r"([А-ЯЁ][а-яё]+\s+государственн\w+\s+(?:техническ\w+\s+)?(?:университет\w*|колледж\w*))",
        # Аббревиатура (ДГТУ и т.п.) ищется отдельно в extract_university
        # строго заглавными: иначе IGNORECASE ловит окончания обычных слов
        # («суббо[ту]», «пятницу» и т.п.).
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
    "reason": [
        r"причин\w*[:\s]+([^\n]{3,200})",
        r"\bв\s+связи\s+(?:с\s+)?([^\n]{3,200})",
    ],
    "start_date": [
        r"дата\s+начала[:\s]*(\d{2}\.\d{2}\.\d{4})",
        r"дата\s+начала[^\d\n]{0,40}(\d{2}\.\d{2}\.\d{4})",
    ],
    "end_date": [
        r"дата\s+окончания[:\s]*(\d{2}\.\d{2}\.\d{4})",
        r"дата\s+окончания[^\d\n]{0,40}(\d{2}\.\d{2}\.\d{4})",
    ],
    "application_date": [
        r"дата\s+(?:подачи\s+)?заявлени\w*[:\s]*(\d{2}\.\d{2}\.\d{4})",
        r"дата\s+подпис[ьи][:\s]*(\d{2}\.\d{2}\.\d{4})",
    ],
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
        for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            value = m.group(1).strip().rstrip(".,;:")
            if value and not _is_service_words(value):
                return value
    return None


# Служебные слова после «выдана/дана»: «для предоставления по...» —
# не ФИО. Список общий, а не под конкретный вуз.
_NAME_STOP = frozenset({
    "для", "предоставления", "предъявления", "месту", "требования",
    "справки", "справка", "документа", "места", "настоящая",
    "дата", "рождения", "года", "месяца",
})
_NAME_CONTEXT_STOP = frozenset({
    "студента", "студентки", "курс", "курса", "факультет", "факультета",
    "группа", "группы", "ректору", "заявление", "указать", "полностью",
    "академический", "отпуск",
})


def _is_service_words(value: str) -> bool:
    words = re.findall(r"[А-Яа-яЁё]+", value.lower())
    return bool(words) and words[0] in _NAME_STOP


def extract_student_name(text: str) -> str | None:
    for pattern in PATTERNS.get("student_name", []):
        for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            value = m.group(1).strip().rstrip(".,;:")
            if value and not _is_service_words(value):
                return value

    # В типовом заявлении ФИО вписано над подписью "(Ф.И.О. указать полностью)".
    # Ищем имя в ближайших строках перед этой подписью: отдельного префикса
    # "ФИО:" у рукописного значения обычно нет.
    lines = text.splitlines()
    for index, line in enumerate(lines):
        fio_label = re.search(r"ф\s*\.?\s*и\s*\.?\s*о\.?", line, re.IGNORECASE)
        if not fio_label:
            continue
        candidates = [line[:fio_label.start()]]
        candidates.extend(lines[max(0, index - 3):index][::-1])
        for candidate in candidates:
            words = re.findall(r"\b[А-ЯЁ][а-яё]{2,}(?:-[А-ЯЁ][а-яё]{2,})?\b", candidate)
            if len(words) < 2 or len(words) > 3:
                continue
            if any(word.casefold() in _NAME_CONTEXT_STOP for word in words):
                continue
            return " ".join(words)
    return None


_ABBR_RE = re.compile(r"\b([А-ЯЁ]{2,8}(?:ГУ|ГТУ|ГАУ|ПГУ|ТУ|ИУ|АСУ))\b")


def extract_university(text: str) -> str | None:
    """Название вуза: сначала полные формы, аббревиатура — только ЗАГЛАВНЫМИ.

    Отдельный проход без IGNORECASE: иначе шаблон аббревиатур ловит
    окончания обычных слов («суббо[ту]», «пятницу»).
    Строка с УНИВЕРСИТЕТ/ИНСТИТУТ + следующая строка — общий случай
    («... УНИВЕРСИТЕТ» + «ВЫСШАЯ ШКОЛА ЭКОНОМИКИ»), а не патч под ВШЭ.
    """
    for pattern in PATTERNS.get("university", []):
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            value = m.group(1).strip().rstrip(".,;:").strip(" \t\"«»'®©*`")
            if value:
                return value
    lines = [line.strip(" \t\"«»'") for line in text.splitlines()]
    for i, line in enumerate(lines):
        if not re.search(r"университет|институт|академия", line, re.IGNORECASE):
            continue
        if len(line) < 5:
            continue
        candidate = line.strip().rstrip(".,;:").strip(" \t\"«»'®©*`")
        # Название часто разбито на 2 строки заглавными
        # («...УНИВЕРСИТЕТ» / «ВЫСШАЯ ШКОЛА ЭКОНОМИКИ»).
        if i + 1 < len(lines):
            nxt = lines[i + 1].strip().rstrip(".,;:").strip(" \t\"«»'®©*`")
            if nxt and len(nxt) >= 4 and (nxt.isupper() or re.search(
                    r"школа|экономики|институт|университет|академия|колледж", nxt, re.IGNORECASE)):
                if len(candidate) + len(nxt) <= 160:
                    candidate = f"{candidate} {nxt}"
        if len(candidate) >= 8:
            return candidate
    # Запасной уровень: строка с «экономики» без surviving-слова
    # «университет» — OCR иногда полностью теряет строку-заголовок
    # (шапка ВШЭ прочиталась мусором, уцелела только вторая строка).
    for line in lines:
        cleaned = line.strip().rstrip(".,;:").strip(" \t\"«»'®©*`")
        if len(cleaned) >= 8 and re.search(r"экономики", cleaned, re.IGNORECASE):
            return cleaned
    for m in _ABBR_RE.finditer(text):
        # Требуем, чтобы совпадение было написано заглавными
        # (допускаем скобки/кавычки вокруг, но не «Субботу»).
        token = m.group(1)
        if token.isupper():
            return token
    return None


_ORDER_NUMBER_HINT = re.compile(r"приказ|распоряжен|зачислен", re.IGNORECASE)


def extract_document_number(text: str) -> str | None:
    """Номер документа, а не № школы («МБОУ СОШ № 28») и не № приказа."""
    for pattern in PATTERNS.get("document_number", []):
        for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            value = m.group(1).strip().rstrip(".,;:")
            if not value:
                continue
            left = text[max(0, m.start() - 60):m.start()]
            # Не отбрасываем номер справки из-за слова «школа» в шапке:
            # OCR может склеить весь документ в один абзац. Номер школы
            # обычно стоит непосредственно после «школа/СОШ/МБОУ».
            school_marker_before_number = re.search(
                r"(?:школ\w*|сош|мбоу|мбдоу|маоу|лице\w*|гимнази\w*)"
                r"(?:\s+[\w«»\"'’-]+){0,2}\s*$",
                left,
                re.IGNORECASE,
            )
            if school_marker_before_number or _ORDER_NUMBER_HINT.search(left):
                continue
            return value
    return None


_INTERNSHIP_DATE = (
    r"(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|"
    r"\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|"
    r"августа|сентября|октября|ноября|декабря)\s+\d{4})"
)


def _parse_internship_date(value: str) -> tuple[str, str, date | None] | None:
    month = _parse_month_date(value)
    if month:
        return month
    parsed = _parse_date_token(value.strip().replace("-", "."))
    return parsed if parsed and parsed[1] == "day" else None


def extract_internship_period(text: str) -> str | None:
    """Извлекает явно указанный диапазон практики с учетом OCR-вариантов дат."""
    normalized = _normalize_spaced_full_dates(text)
    flat = re.sub(r"\s+", " ", normalized)
    pattern = re.compile(
        rf"(?P<start>{_INTERNSHIP_DATE})\s*(?:г(?:ода)?\.?\s*)?"
        rf"(?:\bпо\b|\bдо\b|\s+[–—-]\s+)\s*"
        rf"(?P<end>{_INTERNSHIP_DATE})",
        re.IGNORECASE,
    )
    candidates: list[tuple[int, str, str]] = []
    for match in pattern.finditer(flat):
        start = _parse_internship_date(match.group("start"))
        end = _parse_internship_date(match.group("end"))
        if not start or not end:
            continue
        context = flat[max(0, match.start() - 140):match.end() + 40]
        practice_context = bool(re.search(r"практик|период", context, re.IGNORECASE))
        prefix = flat[max(0, match.start() - 12):match.start()]
        starts_with_from = bool(re.search(r"\bс\s*$", prefix, re.IGNORECASE))
        if not practice_context and not starts_with_from:
            continue
        candidates.append((2 if practice_context else 1, start[0], end[0]))
    if not candidates:
        return None
    _, start_value, end_value = max(candidates, key=lambda item: item[0])
    return f"{start_value} – {end_value}"


_INTERNSHIP_GRADE = re.compile(
    r"\b(?:отлично|хорошо|удовлетворительно|неудовлетворительно|"
    r"зачтено|не\s+зачтено)\b|\b[2-5]\b",
    re.IGNORECASE,
)


def extract_internship_grade(text: str) -> str | None:
    """Ищет оценку в формулировках «оценить на отлично» и «оценка: ...»."""
    for match in re.finditer(r"\bоцен\w*\b[^.!?\n]{0,100}", text, re.IGNORECASE):
        grade = _INTERNSHIP_GRADE.search(match.group(0))
        if grade:
            return re.sub(r"\s+", " ", grade.group(0)).strip().lower()
    return None


def _date_in_issue_fragment(text: str) -> str | None:
    month = _parse_month_date(text)
    if month:
        return month[0]
    for match in re.finditer(r"(?<!\d)\d{1,2}[./-]\d{1,2}[./-]\d{2,4}(?!\d)", text):
        parsed = _parse_internship_date(match.group(0))
        if parsed:
            return parsed[0]
    return None


def extract_internship_issue_date(text: str) -> str | None:
    """Читает дату выдачи из строки номера документа, а не из текста практики."""
    normalized = _normalize_spaced_full_dates(text)
    flat = re.sub(r"\s+", " ", normalized)
    number = extract_document_number(flat)
    if number:
        marker = re.compile(
            rf"(?:№|N\s*[оo]?\.?|#)\s*{re.escape(number)}(?![\w./-])",
            re.IGNORECASE,
        )
        for match in marker.finditer(flat):
            tail = flat[match.end():match.end() + 120]
            issued = re.search(r"\bот\b", tail, re.IGNORECASE)
            if issued:
                value = _date_in_issue_fragment(tail[issued.end():])
                if value:
                    return value

    for match in re.finditer(r"\b(?:дата\s+выдачи|дата\s+справки)\b", flat, re.IGNORECASE):
        value = _date_in_issue_fragment(flat[match.end():match.end() + 100])
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


_DATE_TOKEN = r"(?<!\d)(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}[./]\d{4}|\d{1,2}[./]\d{1,2}|\d{4})(?!\d)"

_RU_MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}
_MONTH_DATE_RE = re.compile(
    r"(?<!\d)(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})(?!\d)",
    re.IGNORECASE,
)


def _parse_month_date(text: str) -> tuple[str, str, date | None] | None:
    """Дата прописью: «30 июня 2024», «01 сентября 2019» — общий случай."""
    m = _MONTH_DATE_RE.search(text)
    if not m:
        return None
    try:
        parsed = date(int(m.group(3)), _RU_MONTHS[m.group(2).lower()], int(m.group(1)))
        return parsed.strftime("%d.%m.%Y"), "day", parsed
    except ValueError:
        return None


def _parse_date_token(value: str) -> tuple[str, str, date | None] | None:
    """Нормализует полную или частично распознанную дату без выдумывания её частей."""
    parts = re.split(r"[./-]", value)
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


_SPACED_FULL_DATE_RE = re.compile(
    r"(?<!\d)[«\"'(\[]?\s*(\d{1,2})\s*[»\"')\]]?"
    r"[./\s-]+(\d{1,2})[./\s-]+((?:19|20)\d{2})(?!\d)"
)


def _normalize_spaced_full_dates(text: str) -> str:
    """Normalize form dates such as `с «10» 09 2018 г.` to `10.09.2018`."""
    def normalize(match: re.Match) -> str:
        try:
            parsed = date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        except ValueError:
            return match.group(0)
        return parsed.strftime("%d.%m.%Y")

    return _SPACED_FULL_DATE_RE.sub(normalize, text)


def _academic_leave_date_range(text: str) -> tuple[str, str] | None:
    """Read the requested leave range, then the previously granted range."""
    normalized = _normalize_spaced_full_dates(text)
    flat = re.sub(r"\s+", " ", normalized)
    pattern = re.compile(
        rf"\bс\s*({_DATE_TOKEN})\s*(?:г(?:ода)?\.?\s*)?"
        rf"[\s,;:–—-]{{0,20}}\bпо\s*({_DATE_TOKEN})",
        re.IGNORECASE,
    )
    candidates: list[tuple[int, int, str, str]] = []
    for match in pattern.finditer(flat):
        start = _parse_date_token(match.group(1))
        end = _parse_date_token(match.group(2))
        if not start or not end or start[1] != "day" or end[1] != "day":
            continue
        prefix = flat[max(0, match.start() - 220):match.start()]
        if re.search(r"\bпрошу\b.{0,180}академическ\w*\s+отпуск", prefix, re.IGNORECASE):
            priority = 2
        elif re.search(r"академическ\w*\s+отпуск.{0,120}предоставлен", prefix, re.IGNORECASE):
            priority = 1
        else:
            priority = 0
        candidates.append((priority, match.start(), start[0], end[0]))
    if not candidates:
        return None
    _, _, start_value, end_value = max(candidates, key=lambda item: (item[0], -item[1]))
    return start_value, end_value


def _academic_leave_reason(text: str) -> str | None:
    match = re.search(
        r"\bв\s+связи\s+(?:с\s+)?([^\n]{3,200})",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    value = re.split(
        r"\(?\s*указать\s+основан|\bдата\s+подпис|\bподпис[ьи]\b",
        match.group(1),
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    value = re.sub(r"[_\s]+", " ", value).strip(" \t.,;:—–-")
    if len(re.findall(r"[А-Яа-яЁёA-Za-z]{2,}", value)) < 2:
        return None
    return value or None


def _date_after_label(text: str, label: str) -> tuple[str, str, date | None] | None:
    for match in re.finditer(label, text, re.IGNORECASE):
        # Между подписью поля и его датой OCR часто оставляет номер приказа,
        # поэтому нельзя ограничивать поиск первым числом.
        tail = text[match.end():match.end() + 140].splitlines()[0]
        month = _parse_month_date(tail)
        if month:
            return month
        for candidate in re.finditer(_DATE_TOKEN, tail):
            parsed = _parse_date_token(candidate.group(0))
            if parsed:
                return parsed
    return None


def _enrollment_date(text: str) -> tuple[str, str, date | None] | None:
    """Use only a date written directly after an admission-date statement."""
    patterns = (
        r"\b\u0434\u0430\u0442\u0430\s+\u0437\u0430\u0447\u0438\u0441\u043b\u0435\u043d\u0438\w*\b",
        r"\b\u0437\u0430\u0447\u0438\u0441\u043b\u0435\u043d\w*\s+(?:\u0441|\u043d\u0430|\u0432)\b",
        r"\bзачислен\w*\s+на\s+\d+\s*курс\b",
        # Общий случай «Приказ о зачислении № 5703/у от 04.08.2014» —
        # дата стоит после номера приказа, а не после «зачислен».
        # Без \b после №: № — не буква, границы слова там нет.
        r"\bзачислении\s+\u2116",
        r"\bприступил\w*\s+к\s+обучени\w*\b",
        r"\bначал\w*\s+обучени\w*\b",
        r"\bпринят\w*\s+(?:в|на)\b",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            # Дата может стоять не сразу («... в МБОУ СОШ № 28 с 01.09.2011»),
            # поэтому ищем «с ДАТА» в хвосте, а не только в начале.
            tail = text[match.end():match.end() + 80].splitlines()[0]
            month = _parse_month_date(tail)
            if month:
                return month
            direct = re.match(rf"\s*[:#\u2116\u2013\u2014-]?\s*({_DATE_TOKEN})", tail)
            if direct:
                parsed = _parse_date_token(direct.group(1))
                if parsed:
                    return parsed
            # «с 01.09.2011» и «от 04.08.2014» (после № приказа).
            dated = re.search(rf"\b[сc]\s*({_DATE_TOKEN})", tail, re.IGNORECASE)
            if dated:
                parsed = _parse_date_token(dated.group(1))
                if parsed:
                    return parsed
            ordered = re.search(rf"\bот\s*({_DATE_TOKEN})", tail, re.IGNORECASE)
            if ordered:
                parsed = _parse_date_token(ordered.group(1))
                if parsed:
                    return parsed
            month_after_c = re.search(
                r"\b[сc]\s+(\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4})",
                tail, re.IGNORECASE)
            if month_after_c:
                parsed = _parse_month_date(month_after_c.group(1))
                if parsed:
                    return parsed
    return None


_PERIOD_SKIP_HINT = re.compile(
    r"каникул|отпуск|расписани|понедельник|вторник|сред[ау]|четверг|пятниц|суббот|воскресен|часов|уроков|перемен",
    re.IGNORECASE,
)


def _context_of(text: str, pos: int, radius: int = 80) -> str:
    return text[max(0, pos - radius):pos]


_RIGHT_SKIP_HINT = re.compile(r"часов|уроков|перемен", re.IGNORECASE)


def _study_period_details(text: str) -> tuple[str, str | None]:
    """Извлекает подтверждённые границы периода и объясняет восстановление даты."""
    notes: list[str] = []
    enrollment = _enrollment_date(text)

    start = end = None
    range_pattern = rf"\bс\s*({_DATE_TOKEN})[^\n]{{0,50}}?\b(?:по|до)\s*({_DATE_TOKEN})"
    for match in re.finditer(range_pattern, text, re.IGNORECASE):
        # Пропускаем расписание («с 08.30 до 14.30 часов») и каникулы —
        # это не период обучения. Метка каникул/расписания стоит ПЕРЕД
        # диапазоном («Каникулы с...»), поэтому смотрим только левый
        # контекст + сам фрагмент. Правый контекст проверяем лишь на
        # «часов/уроков», иначе «Период с...по.... Каникулы с...» в
        # однострочном OCR-тексте отменит и корректный период.
        left = _context_of(text, match.start())
        if _PERIOD_SKIP_HINT.search(left + " " + match.group(0)):
            continue
        if _RIGHT_SKIP_HINT.search(text[match.end():match.end() + 20]):
            continue
        candidate_start = _parse_date_token(match.group(1))
        candidate_end = _parse_date_token(match.group(2))
        if candidate_start and candidate_end:
            # Время вида 08.30 парсится как day_month — для периода нужны
            # полные даты, иначе «08.30 – 14.30» станет периодом.
            if candidate_start[1] != "day" or candidate_end[1] != "day":
                continue
            start, end = candidate_start, candidate_end
            break

    if start is None:
        start = _date_after_label(text, r"\b(?:дата\s+)?начала\s+обучени\w*")
    if end is None:
        end = _date_after_label(text, r"\b(?:дата\s+)?(?:завершени\w*|окончани\w*)\s+обучени\w*")
    if end is None:
        # Общий случай «срок окончания обучения 30 июня 2024» —
        # дата прописью, а не 30.06.2024.
        for m in re.finditer(
            r"(?:окончани\w*|завершени\w*|срок\s+окончания)\s+обучени\w*[^\n]{0,40}",
            text, re.IGNORECASE,
        ):
            month = _parse_month_date(m.group(0))
            if month:
                end = month
                break

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
    if end and not start and not enrollment:
        notes.append("Дата зачисления не распознана; начало периода не восстановлено.")
    if start and start[1] != "day" and not enrollment:
        notes.append(f"Дата начала распознана частично ({start[0]}).")

    value = " – ".join(item[0] for item in (start, end) if item)
    return value or "не найдено", " ".join(notes) or None


def extract_study_period(text: str) -> str:
    """Собирает период обучения, используя дату зачисления как достоверное начало."""
    return _study_period_details(text)[0]


def _clean_program_title(title: str) -> str:
    """Срезает хвосты OCR-мусора («Строительство ы a» → «Строительство»).

    Удаляются только строчные фрагменты из 1-2 букв в конце; аббревиатуры
    заглавными («МЭИ») не трогаем.
    """
    cleaned = re.sub(r"(?:\s+[а-яёa-z]{1,2})+\.?$", "", title.strip()).strip().rstrip(".,;:")
    return cleaned


def extract_program(text: str) -> str:
    """Код специальности + название (код до или после названия)."""
    matches = re.finditer(
        r"(?<!\d)(\d{2}\.\d{2}\.\d{2})(?!\.\d{2})\s+([А-ЯЁа-яё][^\n]{3,120})",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    for match in matches:
        title = _clean_program_title(match.group(2))
        # OCR sometimes sees a short date (e.g. 10.06.20 г.) as a code.
        if re.match(r"(?i)^г(?:од)?(?:\.|\s|$)", title):
            continue
        if len(re.findall(r"[А-Яа-яЁёA-Za-z]{3,}", title)) < 1:
            continue
        return f"{match.group(1)} {title}".rstrip('.')
    # Общий случай «"Востоковедение и африканистика"(58.03.01)» —
    # название до кода в скобках.
    for match in re.finditer(
        r"([А-ЯЁA-Z«\"][\w\s\-«»\"]{3,100}?)\(\s*(\d{2}\.\d{2}\.\d{2})\s*\)",
        text,
    ):
        title = _clean_program_title(match.group(1).strip(" \t\"«»'"))
        if len(title) >= 4 and not _is_service_words(title):
            return f"{match.group(2)} {title}"
    return "не найдено"


def extract_configured_value(text: str, definition: dict[str, Any]) -> str | None:
    """Read a value following a field label/alias supplied by the rules config."""
    aliases = [definition.get("label", ""), *definition.get("aliases", [])]
    lines = text.splitlines()
    for line_index, line in enumerate(lines):
        for alias in aliases:
            if not isinstance(alias, str) or not alias.strip():
                continue
            label_pattern = re.escape(alias.strip()).replace(r"\ ", r"\s+")
            match = re.search(rf"(?<!\w){label_pattern}(?!\w)\s*[:：#№–—-]?\s*(.*)$",
                              line, re.IGNORECASE)
            if not match:
                continue
            candidate = match.group(1).strip(" \t:：#№–—-")
            if not candidate and line_index + 1 < len(lines):
                candidate = lines[line_index + 1].strip(" \t:：#№–—-")
            if not candidate:
                continue

            kind = definition.get("kind", "text")
            if kind == "date":
                found = re.search(r"(?<!\d)(?:\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}-\d{2}-\d{2})(?!\d)", candidate)
                return found.group(0) if found else None
            if kind == "boolean":
                found = re.search(r"(?i)\b(да|нет|есть|присутствует|отсутствует|найдено|не\s+обнаружено)\b", candidate)
                return found.group(0) if found else None
            return candidate.rstrip(".,;:") or None
    return None


def extract_fields(text: str, doc_type: str,
                   field_definitions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    source_text = (
        _normalize_spaced_full_dates(text)
        if doc_type in {"academic_leave", "internship_certificate"}
        else text
    )
    leave_date_range = (
        _academic_leave_date_range(source_text) if doc_type == "academic_leave" else None
    )
    fields: dict[str, Any] = {}
    configured = {item.get("name"): item for item in (field_definitions or [])
                  if isinstance(item, dict) and isinstance(item.get("name"), str)}
    known_type = doc_type in FIELDS_BY_TYPE
    wanted = FIELDS_BY_TYPE.get(doc_type)
    if wanted is None:
        wanted = list(configured)

    for field in wanted:
        if field in ("signature", "stamp"):
            fields[field] = "не найдено"
            continue

        if not known_type and field in configured:
            value = extract_configured_value(source_text, configured[field])
        else:
            value = extract_field(source_text, PATTERNS.get(field, []))
            if not value and field in configured:
                value = extract_configured_value(source_text, configured[field])

        # спец-нормализация
        if field == "study_form":
            value = normalize_study_form(value)
        elif field == "study_period":
            value, note = _study_period_details(text)
            if note:
                fields["study_period_note"] = note
        elif field == "program":
            value = extract_program(text)
        elif field == "internship_period" and doc_type == "internship_certificate":
            value = extract_internship_period(source_text)
        elif field == "grade" and doc_type == "internship_certificate":
            value = extract_internship_grade(source_text)
        elif field == "student_name":
            value = extract_student_name(source_text)
            if not value and field in configured:
                value = extract_configured_value(source_text, configured[field])
        elif field == "university":
            value = extract_university(source_text)
            if not value and field in configured:
                value = extract_configured_value(source_text, configured[field])
        elif field == "document_number":
            value = extract_document_number(source_text)
            if not value and field in configured:
                value = extract_configured_value(source_text, configured[field])
        elif field == "issue_date" and doc_type == "internship_certificate":
            value = extract_internship_issue_date(source_text) or value
        elif field == "reason":
            value = _academic_leave_reason(source_text) or value
        elif field in {"start_date", "end_date"} and not value and leave_date_range:
            value = leave_date_range[0 if field == "start_date" else 1]
        elif field == "application_date" and not value:
            parsed = _date_after_label(
                source_text,
                r"\bдата\s+(?:(?:подачи\s+)?заявлени\w*|подпис[ьи])",
            )
            value = parsed[0] if parsed else None

        fields[field] = value or "не найдено"

    return fields
