"Backend 2: POST /answer — поиск правил и проверка полей документа."

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from backend.models import Document, ServiceAnswer
from backend.answer_llm import AnswerLlmSettings, select_evidence
from backend.rules import KnowledgeBase, NO_ANSWER_TEXT, answer_question, load_knowledge_base

DEFAULT_RULES_PATH = Path(__file__).with_name("data") / "rules.json"
logger = logging.getLogger(__name__)


class HistoryMessage(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    role: Literal["user", "assistant"]
    content: str


class AnswerRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    question: str = Field(min_length=1, max_length=5000)
    conversation_id: str | None = Field(default=None, max_length=100)
    document: Document | None = None
    history: list[HistoryMessage] = Field(default_factory=list, max_length=20)


@asynccontextmanager
async def lifespan(app: FastAPI):
    path = Path(os.getenv("RULES_PATH", str(DEFAULT_RULES_PATH)))
    if path.exists():
        app.state.knowledge_base = load_knowledge_base(path)
    elif "RULES_PATH" in os.environ:
        # Опечатка в настроенном пути не должна незаметно включать другую базу.
        raise FileNotFoundError(f"База правил не найдена: {path}")
    else:
        logger.warning("База правил отсутствует: %s", path)
        app.state.knowledge_base = KnowledgeBase()
    settings = AnswerLlmSettings.from_env()
    app.state.answer_llm_settings = settings
    client = httpx.AsyncClient(follow_redirects=False, trust_env=False) if settings is not None else None
    app.state.answer_llm_client = client
    try:
        yield
    finally:
        if client is not None:
            await client.aclose()


app = FastAPI(title="Онлайн-деканат: логика и правила", lifespan=lifespan)


@app.get("/health")
async def health(request: Request):
    base = request.app.state.knowledge_base
    return {"status": "ok", "knowledge_base": base.title,
            "clauses": len(base.clauses), "document_types": list(base.document_types)}


@app.post("/answer", response_model=ServiceAnswer)
async def answer(data: AnswerRequest, request: Request):
    question = data.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Вопрос не должен быть пустым")
    base = request.app.state.knowledge_base
    fallback = answer_question(base, question, data.document, data.history)
    # Known field/rule questions stay immediate and deterministic. The optional
    # model broadens matching only for questions that could not be answered.
    if not fallback["answer"].startswith(NO_ANSWER_TEXT):
        return fallback
    selection = await select_evidence(
        base, question, data.document, data.history,
        request.app.state.answer_llm_settings, request.app.state.answer_llm_client,
    )
    if selection is None:
        return fallback
    return answer_question(
        base, question, data.document, data.history,
        selected_clause_ids=selection.clause_ids, selected_field_ids=selection.field_ids,
    )
