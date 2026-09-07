"""Validation and buffering for untrusted multipart document uploads."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import PurePath

from fastapi import UploadFile


class FileValidationError(ValueError):
    """An upload did not meet the document file policy."""


@dataclass
class ValidatedUpload:
    original_filename: str
    mime_type: str
    size_bytes: int
    checksum: str
    content: tempfile.SpooledTemporaryFile[bytes]

    def close(self) -> None:
        self.content.close()


_TYPES_BY_EXTENSION = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def _safe_filename(filename: str | None) -> str:
    if not filename:
        raise FileValidationError("a filename is required")
    # Upload filenames are untrusted metadata: never retain a client path.
    normalized = filename.replace("\\", "/")
    name = PurePath(normalized).name
    if name in {"", ".", ".."} or len(name) > 1024:
        raise FileValidationError("invalid filename")
    if "\x00" in name or any(ord(character) < 32 for character in name):
        raise FileValidationError("invalid filename")
    return name


def _detect_mime_type(sample: bytes) -> str:
    if sample.startswith(b"%PDF-"):
        return "application/pdf"
    if sample.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if sample.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    raise FileValidationError("file content is not a supported PDF, PNG, or JPEG")


async def validate_upload(upload: UploadFile, *, max_bytes: int) -> ValidatedUpload:
    """Read a bounded upload, verify its signature, and calculate SHA-256.

    Client-provided MIME types are intentionally not trusted.  The returned file
    is rewound and can be passed directly to private object storage.
    """
    if max_bytes <= 0:
        raise RuntimeError("MAX_UPLOAD_BYTES must be greater than zero")

    filename = _safe_filename(upload.filename)
    expected_mime_type = _TYPES_BY_EXTENSION.get(os.path.splitext(filename)[1].lower())
    if expected_mime_type is None:
        raise FileValidationError("only PDF, PNG, and JPEG files are supported")

    content = tempfile.SpooledTemporaryFile[bytes](max_size=1024 * 1024, mode="w+b")
    digest = hashlib.sha256()
    size_bytes = 0
    sample = b""
    try:
        while chunk := await upload.read(64 * 1024):
            size_bytes += len(chunk)
            if size_bytes > max_bytes:
                raise FileValidationError(
                    f"file exceeds the {max_bytes}-byte upload limit"
                )
            if len(sample) < 16:
                sample += chunk[: 16 - len(sample)]
            digest.update(chunk)
            content.write(chunk)

        if size_bytes == 0:
            raise FileValidationError("file must not be empty")
        mime_type = _detect_mime_type(sample)
        if mime_type != expected_mime_type:
            raise FileValidationError("filename extension does not match file content")
        content.seek(0)
        return ValidatedUpload(
            original_filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum=digest.hexdigest(),
            content=content,
        )
    except Exception:
        content.close()
        raise
    finally:
        await upload.close()
