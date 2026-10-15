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
        r"ФИО\s+студента[:\s]+([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})",
        r"([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)\s*\(\d{2}\.\d{2}\.\d{4}",
        r"фио[:\s]+([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})",
        r"студент[а]?[:\s]+([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})",
        r"дан[ао]?\s+[_\s]*([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})",
        r"выдан[ао]?\s+([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2})",
        r"что\s+([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)\s+действительно",
    ],
    "university": [
        r"«([^»]{5,120}?(?:университет|институт|академия|колледж)[^»]*?)»",
        r"([А-ЯЁ][а-яё]+\s+государственн\w+\s+(?:техническ\w+\s+)?(?:университет\w*|колледж\w*))",
        # Аббревиатура (МГУ, ДГТУ и т.п.) ищется отдельно в extract_university
        # строго заглавными: иначе IGNORECASE ловит окончания обычных слов.
    ],
    "program": [
        r"Направление\s+подготовки[:\s]+([А-ЯЁ][^\n]{3,120})",
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
        r"Номер\s+и\s+дата\s+выдачи[^\d\n]{0,40}(\d{2}\.\d{2}\.\d{4})",
        r"дата\s+выдачи[:\s]*(\d{2}\.\d{2}\.\d{4})",
        r"выдачи[:\s]*(\d{2}\.\d{2}\.\d{4})",
        r"(?<!\d)(\d{2}\.\d{2}\.\d{4})\s*(?:г\.?\s*)?(?:№|N[oо]?\.?|#)",
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
        r"Сроки\s+практики[:\s]*(\d{2}\.\d{2}\.\d{4}\s*[-–]\s*\d{2}\.\d{2}\.\d{4})",
        r"Сроки\s+практики[:\s]*(с\s+\d{2}\.\d{2}\.\d{4}\s+по\s+\d{2}\.\d{2}\.\d{4})",
        r"(с\s+\d{2}\.\d{2}\.\d{4}\s+по\s+\d{2}\.\d{2}\.\d{4})",
        r"(\d{2}\.\d{2}\.\d{4}\s*[-–]\s*\d{2}\.\d{2}\.\d{4})",
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


def _is_service_words(value: str) -> bool:
    words = re.findall(r"[А-Яа-яЁё]+", value.lower())
    return bool(words) and words[0] in _NAME_STOP


def extract_student_name(text: str) -> str | None:
    for pattern in PATTERNS.get("student_name", []):
        for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            value = m.group(1).strip().rstrip(".,;:")
            if value and not _is_service_words(value):
                return value
    return None


# МГУ — три буквы, заканчивается на ГУ, но префикс всего 1 символ.
# Поэтому {1,8}, а не {2,8}.
_ABBR_RE = re.compile(r"\b([А-ЯЁ]{1,8}(?:ГУ|ГТУ|ГАУ|ПГУ|ТУ|ИУ|АСУ))\b")


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
    # «университет» — OCR иногда полностью теряет строку-заголовок.
    for line in lines:
        cleaned = line.strip().rstrip(".,;:").strip(" \t\"«»'®©*`")
        if len(cleaned) >= 8 and re.search(r"экономики", cleaned, re.IGNORECASE):
            return cleaned
    # МГУ-подобные аббревиатуры: только заглавными.
    for m in _ABBR_RE.finditer(text):
        token = m.group(1)
        if token.isupper():
            return token
    return None


_SCHOOL_NUMBER_HINT = re.compile(r"школ\w*|сош|мбоу|мбдоу|маоу|лице\w*|гимнази\w*|класс", re.IGNORECASE)
_ORDER_NUMBER_HINT = re.compile(r"приказ|распоряжен|зачислен", re.IGNORECASE)


def extract_document_number(text: str) -> str | None:
    """Номер документа, а не № школы («МБОУ СОШ № 28») и не № приказа."""
    for pattern in PATTERNS.get("document_number", []):
        for m in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            value = m.group(1).strip().rstrip(".,;:")
            if not value:
                continue
            # Контекст слева: если рядом школа/СОШ/МБОУ — это № школы,
            # если приказ — это № приказа, а не № справки. Окно 60:
            # «приказом от 20 августа 2019 г. №» длиннее 30 символов.
            left = text[max(0, m.start() - 60):m.start()]
            if _SCHOOL_NUMBER_HINT.search(left) or _ORDER_NUMBER_HINT.search(left):
                continue
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
    """Название специальности; сначала без кода, потом код + название."""
    # 1. "Направление подготовки: X" — без кода специальности.
    m = re.search(r"Направление\s+подготовки[:\s]+([А-ЯЁ][^\n]{3,120})",
                  text, re.IGNORECASE)
    if m:
        title = _clean_program_title(m.group(1))
        if title and len(re.findall(r"[А-Яа-яЁёA-Za-z]{3,}", title)) >= 1:
            return title
    # 2. Код + название.
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
    # 3. Общий случай «"Востоковедение и африканистика"(58.03.01)» —
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
            value = extract_configured_value(text, configured[field])
        else:
            value = extract_field(text, PATTERNS.get(field, []))
            if not value and field in configured:
                value = extract_configured_value(text, configured[field])

        # спец-нормализация
        if field == "study_form":
            value = normalize_study_form(value)
        elif field == "study_period":
            value, note = _study_period_details(text)
            if note:
                fields["study_period_note"] = note
        elif field == "program":
            value = extract_program(text)
        elif field == "student_name":
            value = extract_student_name(text)
            if not value and field in configured:
                value = extract_configured_value(text, configured[field])
        elif field == "university":
            value = extract_university(text)
            if not value and field in configured:
                value = extract_configured_value(text, configured[field])
        elif field == "document_number":
            value = extract_document_number(text)
            if not value and field in configured:
                value = extract_configured_value(text, configured[field])

        fields[field] = value or "не найдено"

    return fields