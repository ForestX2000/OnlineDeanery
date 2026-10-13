"""Словарь частых ошибок OCR (message.txt, вариант A).

Быстрая детерминированная альтернатива LLM-постобработке (Qwen3.5-4B на CPU
даёт 1–2 минуты на запрос — для пайплайна недопустимо). Замены цело-словные,
регистронезависимые, регистр восстанавливается по исходному написанию.
Применяется к OCR-тексту ДО regex-извлечения (см. ml2/main.py).
LLM-исправление (ml2/llm.py) остаётся следующим этапом для сложных случаев.
"""

from __future__ import annotations

import re

# Ключ — как пишет OCR, значение — правильное написание.
# Источники: примеры из message.txt + замер PaddleOCR-VL-1.5 на baton.png (CER 0.10).
OCR_FIXES: dict[str, str] = {
    # ФИО
    "данил": "Даниил",
    "даннил": "Даниил",
    "серевич": "Сергеевич",
    # Вуз
    "лонкего": "Донского",
    "домскон": "Донской",
    "гонской": "Донской",
    "сонской": "Донской",
    "снской": "Донской",
    "тэхнигский": "технический",
    "тэхнический": "технический",
    "унивескать": "университет",
    "выспиего": "высшего",
    "выспио": "высшего",
    "пахн": "наук",
    "госсииской": "Российской",
    "дту": "ДГТУ",
    "лту": "ДГТУ",
    "дпу": "ДГТУ",
    "коллект": "колледж",
    # Программа
    "ниформалонные": "Информационные",
    "программрование": "программирование",
    # Служебные слова справки
    "дебютгельно": "действительно",
    "кладется": "является",
    "обучалошмся": "обучающимся",
}

_WORD_RE_CACHE: dict[str, re.Pattern] = {}


def _pattern(word: str) -> re.Pattern:
    if word not in _WORD_RE_CACHE:
        _WORD_RE_CACHE[word] = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
    return _WORD_RE_CACHE[word]


def _restore_case(matched: str, replacement: str) -> str:
    if matched.isupper():
        return replacement.upper()
    if matched[0].isupper():
        return replacement[0].upper() + replacement[1:]
    return replacement[0].lower() + replacement[1:] if replacement else replacement


def apply_ocr_fixes(text: str) -> str:
    """Применяет словарь OCR_FIXES к тексту. Пустой/нестроковый ввод возвращает как есть."""
    if not isinstance(text, str) or not text:
        return text
    for wrong, right in OCR_FIXES.items():
        text = _pattern(wrong).sub(lambda m: _restore_case(m.group(0), right), text)
    return text
