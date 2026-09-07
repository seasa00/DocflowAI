"""Create the initial DocFlow persistence schema.

Revision ID: 0001_create_core_database
Revises:
Create Date: 2026-09-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0001_create_core_database"
down_revision = None
branch_labels = None
depends_on = None


account_status = postgresql.ENUM(
    "active", "disabled", name="account_status", create_type=False
)
schema_status = postgresql.ENUM(
    "draft", "enabled", "deprecated", name="schema_status", create_type=False
)
document_processing_status = postgresql.ENUM(
    "uploaded", "queued", "processing", "processed", "failed", "deleted",
    name="document_processing_status", create_type=False,
)
extraction_job_state = postgresql.ENUM(
    "queued", "running", "retry_scheduled", "succeeded", "failed",
    name="extraction_job_state", create_type=False,
)
extraction_result_status = postgresql.ENUM(
    "draft", "needs_review", "approved", "rejected", "superseded",
    name="extraction_result_status", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        account_status,
        schema_status,
        document_processing_status,
        extraction_job_state,
        extraction_result_status,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=320), unique=True),
        sa.Column("auth_subject", sa.String(length=255), unique=True),
        sa.Column("status", account_status, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("last_login_metadata", postgresql.JSONB(astext_type=sa.Text())),
        sa.CheckConstraint("email IS NOT NULL OR auth_subject IS NOT NULL", name="ck_users_identity_present"),
    )
    op.create_table(
        "document_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(length=100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_table(
        "schemas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("mapping_rules", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("validation_rules", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("status", schema_status, nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("document_type_id", "key", "version", name="uq_schemas_type_key_version"),
        sa.CheckConstraint("version > 0", name="ck_schemas_version_positive"),
    )
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=1024), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False, unique=True),
        sa.Column("checksum", sa.String(length=128), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("page_count", sa.Integer()),
        sa.Column("processing_status", document_processing_status, nullable=False, server_default="uploaded"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["schema_id"], ["schemas.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("size_bytes >= 0", name="ck_documents_size_nonnegative"),
    )
    op.create_index("ix_documents_owner_user_id", "documents", ["owner_user_id"])
    op.create_index("ix_documents_owner_status", "documents", ["owner_user_id", "processing_status"])
    op.create_table(
        "extraction_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", extraction_job_state, nullable=False, server_default="queued"),
        sa.Column("current_stage", sa.String(length=100)),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("lease_token", postgresql.UUID(as_uuid=True)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(length=100)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["schema_id"], ["schemas.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_extraction_jobs_attempt_nonnegative"),
    )
    op.create_index("ix_extraction_jobs_document_id", "extraction_jobs", ["document_id"])
    op.create_index(
        "ix_extraction_jobs_runnable", "extraction_jobs", ["state", "available_at"],
        postgresql_where=sa.text("state IN ('queued', 'retry_scheduled')"),
    )
    op.create_table(
        "extraction_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("schema_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("result_version", sa.Integer(), nullable=False),
        sa.Column("ocr_artifact_key", sa.String(length=1024)),
        sa.Column("provider", sa.String(length=100)),
        sa.Column("model", sa.String(length=255)),
        sa.Column("provider_metadata", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("raw_candidate_output", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("mapped_data", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("evidence_map", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("validation_issues", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("reviewed_data", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("review_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True)),
        sa.Column("status", extraction_result_status, nullable=False, server_default="draft"),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["job_id"], ["extraction_jobs.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["schema_id"], ["schemas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("document_id", "result_version", name="uq_extraction_results_document_version"),
        sa.CheckConstraint("result_version > 0", name="ck_extraction_results_version_positive"),
        sa.CheckConstraint("review_version >= 0", name="ck_extraction_results_review_version_nonnegative"),
    )
    op.create_index(
        "ix_extraction_results_document_status_version", "extraction_results",
        ["document_id", "status", "result_version"],
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("document_id", postgresql.UUID(as_uuid=True)),
        sa.Column("result_id", postgresql.UUID(as_uuid=True)),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("request_correlation_id", sa.String(length=100)),
        sa.Column("metadata_redacted", postgresql.JSONB(astext_type=sa.Text())),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["result_id"], ["extraction_results.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_logs_document_created", "audit_logs", ["document_id", "created_at"])
    op.create_index("ix_audit_logs_request_correlation_id", "audit_logs", ["request_correlation_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_request_correlation_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_document_created", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_extraction_results_document_status_version", table_name="extraction_results")
    op.drop_table("extraction_results")
    op.drop_index("ix_extraction_jobs_runnable", table_name="extraction_jobs")
    op.drop_index("ix_extraction_jobs_document_id", table_name="extraction_jobs")
    op.drop_table("extraction_jobs")
    op.drop_index("ix_documents_owner_status", table_name="documents")
    op.drop_index("ix_documents_owner_user_id", table_name="documents")
    op.drop_table("documents")
    op.drop_table("schemas")
    op.drop_table("document_types")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_type in (
        extraction_result_status,
        extraction_job_state,
        document_processing_status,
        schema_status,
        account_status,
    ):
        enum_type.drop(bind, checkfirst=True)
