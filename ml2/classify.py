import re

# ключи совпадают с rules.json в backend/
RULES: dict[str, list[tuple[str, int]]] = {
    "academic_leave": [
        (r"академическ\w*\s+отпуск", 5),
        (r"причина\s+отпуска", 4),
        (r"дата\s+начала\s+отпуска", 3),
        (r"дата\s+окончания\s+отпуска", 3),
        (r"заявление", 1),
    ],
    "internship_certificate": [
        (r"практик", 4),
        (r"руководител\w*\s+практики", 4),
        (r"сроки\s+практики", 3),
        (r"организаци", 2),
        (r"оценка", 1),
    ],
    "study_certificate": [
        (r"справка\s+об\s+обучении", 5),
        (r"направление\s+подготовки", 4),
        (r"форма\s+обучения", 3),
        (r"период\s+обучения", 3),
        (r"название\s+вуза|университет", 1),
    ],
}


# определяет тип документа; возвращает (тип, уверенность 0..1)
def classify(text: str) -> tuple[str, float]:
    low = text.lower()
    scores: dict[str, int] = {}
    for doc_type, patterns in RULES.items():
        scores[doc_type] = sum(w for p, w in patterns if re.search(p, low))

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return "неизвестно", 0.0
    return best, round(scores[best] / total, 3)