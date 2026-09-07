"""Untrusted LLM response schemas for invoice extraction."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.database import EvidenceReference, InvoiceDraft


class InvoiceExtractionData(InvoiceDraft):
    """Invoice values as model output, with no tolerance for extra keys."""

    model_config = ConfigDict(extra="forbid")


class InvoiceExtractionOutput(BaseModel):
    """The only JSON shape accepted from an invoice-extraction model.

    Values live below ``data`` so provider wrappers and model commentary cannot
    accidentally be interpreted as invoice fields. Unknown fields are rejected
    instead of silently becoming stored data.
    """

    model_config = ConfigDict(extra="forbid")

    data: InvoiceExtractionData
    evidence: dict[str, list[EvidenceReference]] = Field(default_factory=dict)

    @field_validator("evidence")
    @classmethod
    def evidence_only_names_invoice_fields(
        cls, value: dict[str, list[EvidenceReference]]
    ) -> dict[str, list[EvidenceReference]]:
        permitted = set(InvoiceExtractionData.model_fields)
        unknown = set(value) - permitted
        if unknown:
            raise ValueError(f"evidence contains unknown invoice fields: {sorted(unknown)}")
        return value
