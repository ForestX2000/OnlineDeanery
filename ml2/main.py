from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, JsonValue

from ml2.classify import classify
from ml2.extract import extract_fields
from ml2.llm import fix_fields_with_llm
from ml2.ocr_fixes import apply_ocr_fixes
from ml2.visual import apply_visual_features, link_coordinates


class ExtractRequest(BaseModel):
    ocr_result: dict[str, Any]
    document_type: str | None = None
    field_definitions: list[dict[str, Any]] = Field(default_factory=list)


class ExtractResponse(BaseModel):
    document_type: str | None = None
    fields: dict[str, JsonValue]
    coordinates: list[JsonValue] = []


app = FastAPI(title="ML 2: Extract")


# поля, которые LLM исправляет (там, где OCR врёт)
FIELDS_FOR_LLM = {"student_name", "university", "program"}


# health-check
@app.get("/health")
def health():
    return {"status": "ok"}


# принимает результат OCR, возвращает тип документа и поля
@app.post("/extract", response_model=ExtractResponse)
def extract(data: ExtractRequest):
    text = data.ocr_result.get("text")
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(400, "ocr_result.text пустой или отсутствует")

    # 0. Словарь частых ошибок OCR (быстро, детерминированно) — до classify
    # и regex, чтобы ключевые слова и шаблоны срабатывали. LLM ниже —
    # следующий этап для сложных случаев.
    text = apply_ocr_fixes(text)

    if data.document_type:
        doc_type = data.document_type
    else:
        doc_type, _ = classify(text)

    if doc_type == "неизвестно":
        return ExtractResponse(document_type=None, fields={})

    # 1. regex + правила (быстро, всегда работает)
    fields = extract_fields(text, doc_type, data.field_definitions)
    apply_visual_features(fields, data.ocr_result.get("visual_features"))

    # 2. LLM-исправление для «сложных» полей (только если LLM доступна)
    to_fix = {k: fields.get(k, "не найдено") for k in FIELDS_FOR_LLM if k in fields}
    if to_fix:
        fixed = fix_fields_with_llm(text, doc_type, to_fix)
        if fixed:
            for key, value in fixed.items():
                if value and value != "не найдено":
                    fields[key] = value

    return ExtractResponse(document_type=doc_type, fields=fields,
                           coordinates=link_coordinates(data.ocr_result.get("coordinates"), fields))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ml2.main:app", host="0.0.0.0", port=8003)
