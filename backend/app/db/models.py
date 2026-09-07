"""Relational data model for DocFlow's document-processing lifecycle."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AccountStatus(str, enum.Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class SchemaStatus(str, enum.Enum):
    DRAFT = "draft"
    ENABLED = "enabled"
    DEPRECATED = "deprecated"


class DocumentProcessingStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DELETED = "deleted"


class ExtractionJobState(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    RETRY_SCHEDULED = "retry_scheduled"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ExtractionResultStatus(str, enum.Enum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "email IS NOT NULL OR auth_subject IS NOT NULL",
            name="ck_users_identity_present",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    auth_subject: Mapped[str | None] = mapped_column(String(255), unique=True)
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, name="account_status"),
        nullable=False,
        server_default=AccountStatus.ACTIVE.value,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    documents: Mapped[list[Document]] = relationship(back_populates="owner")
    reviewed_results: Mapped[list[ExtractionResult]] = relationship(
        back_populates="reviewer", foreign_keys="ExtractionResult.reviewer_id"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="actor")


class DocumentType(TimestampMixin, Base):
    __tablename__ = "document_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(nullable=False, server_default=text("true"))

    schemas: Mapped[list[Schema]] = relationship(back_populates="document_type")
    documents: Mapped[list[Document]] = relationship(back_populates="document_type")


class Schema(TimestampMixin, Base):
    __tablename__ = "schemas"
    __table_args__ = (
        UniqueConstraint("document_type_id", "key", "version", name="uq_schemas_type_key_version"),
        CheckConstraint("version > 0", name="ck_schemas_version_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_types.id", ondelete="RESTRICT"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    mapping_rules: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    validation_rules: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[SchemaStatus] = mapped_column(
        Enum(SchemaStatus, name="schema_status"),
        nullable=False,
        server_default=SchemaStatus.DRAFT.value,
    )

    document_type: Mapped[DocumentType] = relationship(back_populates="schemas")
    documents: Mapped[list[Document]] = relationship(back_populates="schema")
    extraction_jobs: Mapped[list[ExtractionJob]] = relationship(back_populates="schema")
    extraction_results: Mapped[list[ExtractionResult]] = relationship(back_populates="schema")


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="ck_documents_size_nonnegative"),
        Index("ix_documents_owner_status", "owner_user_id", "processing_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    document_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_types.id", ondelete="RESTRICT"), nullable=False
    )
    schema_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schemas.id", ondelete="RESTRICT"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(1024), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer)
    processing_status: Mapped[DocumentProcessingStatus] = mapped_column(
        Enum(DocumentProcessingStatus, name="document_processing_status"),
        nullable=False,
        server_default=DocumentProcessingStatus.UPLOADED.value,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner: Mapped[User] = relationship(back_populates="documents")
    document_type: Mapped[DocumentType] = relationship(back_populates="documents")
    schema: Mapped[Schema] = relationship(back_populates="documents")
    extraction_jobs: Mapped[list[ExtractionJob]] = relationship(back_populates="document")
    extraction_results: Mapped[list[ExtractionResult]] = relationship(back_populates="document")
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="document")


class ExtractionJob(TimestampMixin, Base):
    __tablename__ = "extraction_jobs"
    __table_args__ = (
        CheckConstraint("attempt_count >= 0", name="ck_extraction_jobs_attempt_nonnegative"),
        Index(
            "ix_extraction_jobs_runnable",
            "state",
            "available_at",
            postgresql_where=text("state IN ('queued', 'retry_scheduled')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    schema_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schemas.id", ondelete="RESTRICT"), nullable=False
    )
    state: Mapped[ExtractionJobState] = mapped_column(
        Enum(ExtractionJobState, name="extraction_job_state"),
        nullable=False,
        server_default=ExtractionJobState.QUEUED.value,
    )
    current_stage: Mapped[str | None] = mapped_column(String(100))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    lease_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(100))

    document: Mapped[Document] = relationship(back_populates="extraction_jobs")
    schema: Mapped[Schema] = relationship(back_populates="extraction_jobs")
    result: Mapped[ExtractionResult | None] = relationship(back_populates="job", uselist=False)


class ExtractionResult(TimestampMixin, Base):
    __tablename__ = "extraction_results"
    __table_args__ = (
        UniqueConstraint("document_id", "result_version", name="uq_extraction_results_document_version"),
        CheckConstraint("result_version > 0", name="ck_extraction_results_version_positive"),
        CheckConstraint("review_version >= 0", name="ck_extraction_results_review_version_nonnegative"),
        Index("ix_extraction_results_document_status_version", "document_id", "status", "result_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("extraction_jobs.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    schema_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schemas.id", ondelete="RESTRICT"), nullable=False
    )
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)
    result_version: Mapped[int] = mapped_column(Integer, nullable=False)
    ocr_artifact_key: Mapped[str | None] = mapped_column(String(1024))
    provider: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(255))
    provider_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    raw_candidate_output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    mapped_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    evidence_map: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    validation_issues: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    reviewed_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    review_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    status: Mapped[ExtractionResultStatus] = mapped_column(
        Enum(ExtractionResultStatus, name="extraction_result_status"),
        nullable=False,
        server_default=ExtractionResultStatus.DRAFT.value,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    document: Mapped[Document] = relationship(back_populates="extraction_results")
    job: Mapped[ExtractionJob] = relationship(back_populates="result")
    schema: Mapped[Schema] = relationship(back_populates="extraction_results")
    reviewer: Mapped[User | None] = relationship(
        back_populates="reviewed_results", foreign_keys=[reviewer_id]
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="result")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_document_created", "document_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL")
    )
    result_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("extraction_results.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    request_correlation_id: Mapped[str | None] = mapped_column(String(100), index=True)
    metadata_redacted: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    actor: Mapped[User | None] = relationship(back_populates="audit_logs")
    document: Mapped[Document | None] = relationship(back_populates="audit_logs")
    result: Mapped[ExtractionResult | None] = relationship(back_populates="audit_logs")
