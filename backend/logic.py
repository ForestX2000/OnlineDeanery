"""Backend 2: POST /answer — поиск правил и проверка полей документа."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from backend.models import Document, ServiceAnswer
from backend.rules import KnowledgeBase, answer_question, load_knowledge_base

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
    yield


app = FastAPI(title="Онлайн-деканат: логика и правила", lifespan=lifespan)


@app.get("/health")
async def health(request: Request):
    base = request.app.state.knowledge_base
    return {"status": "ok", "knowledge_base": base.title,
            "clauses": len(base.clauses), "document_types": list(base.document_types)}


@app.post("/answer", response_model=ServiceAnswer)
def answer(data: AnswerRequest, request: Request):
    question = data.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Вопрос не должен быть пустым")
    return answer_question(request.app.state.knowledge_base, question, data.document, data.history)
