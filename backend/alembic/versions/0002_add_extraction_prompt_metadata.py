"""Add immutable prompt provenance to extraction results.

Revision ID: 0002_add_extraction_prompt_metadata
Revises: 0001_create_core_database
Create Date: 2026-09-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_add_extraction_prompt_metadata"
down_revision = "0001_create_core_database"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "extraction_results",
        sa.Column("prompt_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Prompt text is deliberately not retained: it may contain document
        # content. Version and content digest make prompts reproducible safely.
    )


def downgrade() -> None:
    op.drop_column("extraction_results", "prompt_metadata")
