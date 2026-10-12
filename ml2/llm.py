import json
import os
import re

import requests

LLM_URL = os.getenv("LLM_URL", "http://host.docker.internal:8081/v1/chat/completions")
LLM_TIMEOUT = 180

FIX_PROMPT = """Ты — ассистент деканата. Ниже — текст справки, распознанный OCR (может содержать ошибки).
Уже извлечённые поля (могут быть с ошибками):
{fields_json}

Исправь ошибки OCR в этих полях. Используй контекст документа.
Правила:
- ФИО: исправь опечатки в имени и отчестве (например, "Данил" → "Даниил", "Серевич" → "Сергеевич").
- Вуз: восстанови правильное название (например, "Лонкего" → "Донского", добавь "университета" если пропущено).
- Программа: восстанови полное название специальности после кода.
- Если поле не найдено — оставь "не найдено".
- Отвечай ТОЛЬКО JSON, без пояснений и markdown.

Пример ответа:
{{"student_name": "Иванов Иван Иванович", "university": "МГУ", "program": "09.02.07 Информационные системы и программирование"}}

Текст OCR:
{ocr_text}
"""


def fix_fields_with_llm(ocr_text: str, doc_type: str, fields: dict) -> dict | None:
    """Отправляет поля и OCR-текст в LLM, получает исправленные значения."""
    try:
        resp = requests.post(
            LLM_URL,
            json={
                "messages": [{
                    "role": "user",
                    "content": FIX_PROMPT.format(
                        ocr_text=ocr_text,
                        fields_json=json.dumps(fields, ensure_ascii=False),
                    ),
                }],
                "temperature": 0.1,
                "max_tokens": 512,
            },
            timeout=LLM_TIMEOUT,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        # вытаскиваем JSON из ответа
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if not m:
            return None

        result = json.loads(m.group(0))
        # оставляем только те поля, которые просили исправить
        return {k: v for k, v in result.items() if k in fields}
    except Exception as e:
        print(f"[WARN] LLM недоступна ({e}), fallback на regex")
        return None