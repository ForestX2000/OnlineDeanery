"""Общий контракт API-шлюза и сервиса правил."""

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from typing import Literal


class ApiModel(BaseModel):
    model_config = ConfigDict(strict=True)


class Source(ApiModel):
    type: str
    reference: str
    url: str | None = None


class Verification(ApiModel):
    status: str
    missing_fields: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class DocumentImage(ApiModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    rotation: Literal[0, 90, 180, 270] = 0


class Document(ApiModel):
    type: str | None = None
    fields: dict[str, JsonValue]
    ocr_text: str = ""
    coordinates: list[JsonValue] = Field(default_factory=list)
    image: DocumentImage | None = None
    visual_features: dict[str, JsonValue] | None = None


class ServiceAnswer(ApiModel):
    answer: str = Field(min_length=1)
    sources: list[Source] = Field(default_factory=list)
    verification: Verification | None = None


class ApiResponse(ServiceAnswer):
    conversation_id: str
    document: Document | None = None
