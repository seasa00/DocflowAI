"""Pydantic schemas for database-backed data and Invoice V1 validation."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db.models import (
    AccountStatus,
    DocumentProcessingStatus,
    ExtractionJobState,
    ExtractionResultStatus,
    SchemaStatus,
)


class ORMModel(BaseModel):
    """Base model that can be built directly from a SQLAlchemy ORM instance."""

    model_config = ConfigDict(from_attributes=True)


class UserRead(ORMModel):
    id: uuid.UUID
    email: str | None
    auth_subject: str | None
    status: AccountStatus
    created_at: datetime
    last_login_at: datetime | None


class UserCreate(BaseModel):
    email: str | None = Field(default=None, max_length=320)
    auth_subject: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def require_auth_identity(self) -> UserCreate:
        if not self.email and not self.auth_subject:
            raise ValueError("email or auth_subject is required")
        return self


class DocumentTypeRead(ORMModel):
    id: uuid.UUID
    key: str
    display_name: str
    description: str | None
    is_enabled: bool
    created_at: datetime


class DocumentTypeCreate(BaseModel):
    key: str = Field(pattern="^[a-z][a-z0-9_]*$", max_length=100)
    display_name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class SchemaRead(ORMModel):
    id: uuid.UUID
    document_type_id: uuid.UUID
    key: str
    version: int = Field(gt=0)
    definition: dict[str, Any]
    mapping_rules: dict[str, Any] | None
    validation_rules: dict[str, Any] | None
    prompt_version: str
    status: SchemaStatus
    created_at: datetime


class SchemaDefinitionCreate(BaseModel):
    document_type_id: uuid.UUID
    key: str = Field(pattern="^[a-z][a-z0-9_]*$", max_length=100)
    version: int = Field(gt=0)
    definition: dict[str, Any]
    mapping_rules: dict[str, Any] | None = None
    validation_rules: dict[str, Any] | None = None
    prompt_version: str = Field(min_length=1, max_length=100)


class DocumentCreate(BaseModel):
    """Validated metadata required after private file storage succeeds."""

    document_type_id: uuid.UUID
    schema_id: uuid.UUID
    original_filename: str = Field(min_length=1, max_length=1024)
    storage_key: str = Field(min_length=1, max_length=1024)
    checksum: str = Field(min_length=1, max_length=128)
    mime_type: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=0)
    page_count: int | None = Field(default=None, ge=1)


class DocumentRead(ORMModel):
    id: uuid.UUID
    owner_user_id: uuid.UUID
    document_type_id: uuid.UUID
    schema_id: uuid.UUID
    original_filename: str
    storage_key: str
    checksum: str
    mime_type: str
    size_bytes: int
    page_count: int | None
    processing_status: DocumentProcessingStatus
    created_at: datetime
    deleted_at: datetime | None


class ExtractionJobRead(ORMModel):
    id: uuid.UUID
    document_id: uuid.UUID
    schema_id: uuid.UUID
    state: ExtractionJobState
    current_stage: str | None
    attempt_count: int = Field(ge=0)
    available_at: datetime
    lease_expires_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    created_at: datetime


class ExtractionJobCreate(BaseModel):
    document_id: uuid.UUID
    schema_id: uuid.UUID
    available_at: datetime | None = None


class EvidenceReference(BaseModel):
    page: int = Field(ge=1)
    text_block_id: str = Field(min_length=1, max_length=255)


class ValidationIssue(BaseModel):
    field: str | None = Field(default=None, max_length=255)
    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)
    severity: str = Field(pattern="^(error|warning)$")


class InvoiceDraft(BaseModel):
    """The V1 invoice candidate shape; unresolved extraction fields remain null."""

    supplier_name: str | None = Field(default=None, max_length=500)
    invoice_number: str | None = Field(default=None, max_length=255)
    issue_date: date | None = None
    due_date: date | None = None
    currency: str | None = Field(default=None, pattern="^[A-Z]{3}$")
    subtotal: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    tax_amount: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    total_amount: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)

    @field_validator("supplier_name", "invoice_number", mode="before")
    @classmethod
    def blank_text_is_missing(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: Any) -> Any:
        return value.strip().upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_invoice_dates_and_amounts(self) -> InvoiceDraft:
        if self.issue_date and self.due_date and self.due_date < self.issue_date:
            raise ValueError("due_date cannot be before issue_date")
        for field_name in ("subtotal", "tax_amount", "total_amount"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must be non-negative")
        return self


class InvoiceApproval(InvoiceDraft):
    """Invoice shape required when a reviewer approves a V1 record."""

    supplier_name: str = Field(min_length=1, max_length=500)
    invoice_number: str = Field(min_length=1, max_length=255)
    issue_date: date
    currency: str = Field(pattern="^[A-Z]{3}$")
    total_amount: Decimal = Field(max_digits=14, decimal_places=2)


class ExtractionResultRead(ORMModel):
    id: uuid.UUID
    document_id: uuid.UUID
    job_id: uuid.UUID
    schema_id: uuid.UUID
    schema_version: int = Field(gt=0)
    result_version: int = Field(gt=0)
    ocr_artifact_key: str | None
    provider: str | None
    model: str | None
    provider_metadata: dict[str, Any] | None
    prompt_version: str
    prompt_metadata: dict[str, Any] | None
    raw_candidate_output: dict[str, Any] | None
    mapped_data: dict[str, Any] | None
    evidence_map: dict[str, list[EvidenceReference]] | None
    validation_issues: list[ValidationIssue] | None
    reviewed_data: dict[str, Any] | None
    review_version: int = Field(ge=0)
    reviewer_id: uuid.UUID | None
    status: ExtractionResultStatus
    approved_at: datetime | None
    created_at: datetime


class ReviewUpdate(BaseModel):
    """A review edit with the version required for optimistic concurrency."""

    review_version: int = Field(ge=0)
    reviewed_data: InvoiceDraft


class AuditLogRead(ORMModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    document_id: uuid.UUID | None
    result_id: uuid.UUID | None
    action: str
    created_at: datetime
    request_correlation_id: str | None
    metadata_redacted: dict[str, Any] | None
