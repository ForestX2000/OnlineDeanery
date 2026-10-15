"Общий контракт API-шлюза, сервиса правил и ORM-модели для PostgreSQL"

import enum
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, JsonValue
from sqlalchemy import (
    Boolean,
    JSON,
    TIMESTAMP,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import relationship
from backend.database import Base

# Существующие Pydantic-модели (контракты API и тестов)


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


# SQLAlchemy ORM модели для PostgreSQL (Личный кабинет и Админка) 


class UserDB(Base):
  __tablename__ = "users"

  user_id = Column(Integer, primary_key=True, index=True)
  username = Column(String(100), unique=True, nullable=False)
  email = Column(String(255), unique=True, nullable=False)
  password_hash = Column(String(255), nullable=False)
  is_bootstrap_admin = Column(
      Boolean, default=False, server_default=text("false"), nullable=False
  )
  role = Column(
      String(50), default="student", nullable=False
  )  # 'student', 'admin'
  created_at = Column(
      TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
  )

  documents = relationship(
      "DocumentDB", back_populates="user", cascade="all, delete"
  )
  requests = relationship(
      "RequestDB", back_populates="user", cascade="all, delete"
  )


class DocumentDB(Base):
  __tablename__ = "documents"

  document_id = Column(Integer, primary_key=True, index=True)
  user_id = Column(
      Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
  )
  file_path = Column(String(512), nullable=False)
  document_type = Column(String(100))
  status = Column(
      String(50), default="pending", nullable=False
  )  # 'pending', 'approved', 'rejected', 'missing_fields'
  uploaded_at = Column(
      TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
  )

  user = relationship("UserDB", back_populates="documents")
  fields = relationship(
      "ExtractedFieldDB", back_populates="document", cascade="all, delete"
  )
  requests = relationship("RequestDB", back_populates="document")


class ExtractedFieldDB(Base):
  __tablename__ = "extracted_fields"

  field_id = Column(Integer, primary_key=True, index=True)
  document_id = Column(
      Integer,
      ForeignKey("documents.document_id", ondelete="CASCADE"),
      nullable=False,
  )
  field_name = Column(String(100), nullable=False)
  field_value = Column(Text)
  bounding_box = Column(JSON)  # Координаты для подсветки на фронтенде

  document = relationship("DocumentDB", back_populates="fields")


class RuleDB(Base):
  __tablename__ = "rules"

  rule_id = Column(Integer, primary_key=True, index=True)
  section_number = Column(String(50), nullable=False)
  title = Column(String(255))
  content = Column(Text, nullable=False)


class AuthTokenDB(Base):
  __tablename__ = "auth_tokens"

  token_hash = Column(String(64), primary_key=True)
  user_id = Column(
      Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
  )
  created_at = Column(
      TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
  )


class RequestDB(Base):
  __tablename__ = "requests"

  request_id = Column(Integer, primary_key=True, index=True)
  user_id = Column(
      Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
  )
  document_id = Column(
      Integer, ForeignKey("documents.document_id", ondelete="SET NULL")
  )
  question_text = Column(Text, nullable=False)
  answer_text = Column(Text)
  document_type = Column(String(100))
  status = Column(String(50), default="resolved", nullable=False)
  created_at = Column(
      TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
  )

  user = relationship("UserDB", back_populates="requests")
  document = relationship("DocumentDB", back_populates="requests")


class AuditLogDB(Base):
  __tablename__ = "audit_logs"

  log_id = Column(Integer, primary_key=True, index=True)
  admin_id = Column(
      Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
  )
  admin_email = Column(String(255))
  # Keep the target id as an audit snapshot; it intentionally has no FK.
  target_user_id = Column(Integer)
  target_document_id = Column(
      Integer, ForeignKey("documents.document_id", ondelete="SET NULL")
  )
  action_type = Column(String(100), nullable=False)
  comment = Column(Text)
  created_at = Column(
      TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
  )

  admin = relationship("UserDB", foreign_keys=[admin_id])
  target_document = relationship("DocumentDB", foreign_keys=[target_document_id])


class UserRole(str, enum.Enum):
    STUDENT = "student"
    ADMIN = "admin"
