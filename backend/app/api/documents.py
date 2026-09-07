"""Document upload API.  Processing begins nowhere in this module."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db_session
from app.db.models import (
    AccountStatus,
    Document,
    DocumentProcessingStatus,
    DocumentType,
    Schema,
    SchemaStatus,
    User,
)
from app.schemas.database import DocumentRead
from app.storage import PrivateObjectStorage, StorageError, get_private_storage
from app.uploads import FileValidationError, validate_upload

router = APIRouter(tags=["documents"])


def _storage_key() -> str:
    return f"documents/{uuid.uuid4()}.bin"


@router.post("/documents", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
@router.post(
    "/documents/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def upload_document(
    file: Annotated[UploadFile, File(description="PDF, PNG, or JPEG document")],
    owner_user_id: Annotated[uuid.UUID, Form()],
    document_type_id: Annotated[uuid.UUID, Form()],
    schema_id: Annotated[uuid.UUID, Form()],
    session: Annotated[Session, Depends(get_db_session)],
    storage: Annotated[PrivateObjectStorage, Depends(get_private_storage)],
) -> Document:
    """Validate, privately store, then atomically persist uploaded metadata."""
    try:
        upload = await validate_upload(file, max_bytes=get_settings().max_upload_bytes)
    except FileValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

    try:
        owner = session.get(User, owner_user_id)
        document_type = session.get(DocumentType, document_type_id)
        schema = session.get(Schema, schema_id)
        if owner is None or owner.status != AccountStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="owner user not found")
        if document_type is None or not document_type.is_enabled:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document type not found")
        if (
            schema is None
            or schema.document_type_id != document_type_id
            or schema.status != SchemaStatus.ENABLED
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="schema is not enabled for this document type",
            )

        key = _storage_key()
        try:
            storage.put(key, upload.content)
        except StorageError as error:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="private storage is unavailable") from error

        document = Document(
            owner_user_id=owner_user_id,
            document_type_id=document_type_id,
            schema_id=schema_id,
            original_filename=upload.original_filename,
            storage_key=key,
            checksum=upload.checksum,
            mime_type=upload.mime_type,
            size_bytes=upload.size_bytes,
            processing_status=DocumentProcessingStatus.UPLOADED,
        )
        try:
            session.add(document)
            session.commit()
            session.refresh(document)
        except Exception as error:
            session.rollback()
            try:
                storage.delete(key)
            except StorageError:
                # The object is inaccessible and a later storage cleanup can remove it.
                pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="could not save document metadata",
            ) from error
        return document
    finally:
        upload.close()
