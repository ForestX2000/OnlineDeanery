"""Общий контракт API-шлюза и сервиса правил."""

from pydantic import BaseModel, ConfigDict, Field, JsonValue


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


class Document(ApiModel):
    type: str | None = None
    fields: dict[str, JsonValue]
    ocr_text: str = ""
    coordinates: list[JsonValue] = Field(default_factory=list)


class ServiceAnswer(ApiModel):
    answer: str = Field(min_length=1)
    sources: list[Source] = Field(default_factory=list)
    verification: Verification | None = None


class ApiResponse(ServiceAnswer):
    conversation_id: str
    document: Document | None = None
