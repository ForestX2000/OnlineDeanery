import re

RULES: dict[str, list[tuple[str, int]]] = {
    "academic_leave": [
        (r"академическ\w*\s+отпуск", 5),
        (r"причин\w*\s+отпуск", 4),
        (r"дат\w*\s+начал\w*\s+отпуск", 3),
        (r"дат\w*\s+окончан\w*\s+отпуск", 3),
        (r"заявлени", 1),
    ],
    "internship_certificate": [
        (r"практик", 4),
        (r"руководител\w*\s+практик", 4),
        (r"срок\w*\s+практик", 3),
        (r"организаци", 2),
        (r"оценк", 1),
    ],
    "study_certificate": [
        # основные маркеры
        (r"справк\w*\s+об\s+обучени", 5),
        (r"направлени\w*\s+подготовк", 4),
        (r"форм\w*\s+обучени", 3),
        (r"период\w*\s+обучени", 3),
        # fallback: гибкие паттерны
        (r"обуча\w+", 2),          # «обучается», «обучающийся»
        (r"университет|институт|академи", 2),
        (r"курс\w*", 1),
        (r"зачислен\w*", 1),
        (r"справк", 1),
    ],
}


def classify(text: str) -> tuple[str, float]:
    """Возвращает (тип, уверенность 0..1)."""
    low = text.lower()
    # Школьная справка — не вузовская «справка об обучении» (п. 3.1):
    # МБОУ/СОШ/ученик/класс без вузовских маркеров — это другой тип,
    # иначе «обучается + справка» ложно даёт study_certificate 1.0.
    if re.search(r"школа|мбоу|мбдоу|маоу|сош\b|ученик\b|\b\d{1,2}[а-я]\s+класс", low) and not re.search(
        r"университет|институт|академия|колледж|вуз|направлени\w*\s+подготовк|зачислен", low
    ):
        return "неизвестно", 0.0
    scores: dict[str, int] = {}
    for doc_type, patterns in RULES.items():
        scores[doc_type] = sum(w for p, w in patterns if re.search(p, low))

    best = max(scores, key=scores.get)
    total = sum(scores.values()) or 1
    if scores[best] == 0:
        return "неизвестно", 0.0
    return best, round(scores[best] / total, 3)