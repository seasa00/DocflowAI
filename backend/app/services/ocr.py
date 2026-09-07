"""OCR abstraction and PaddleOCR implementation.

The normalized artifact deliberately keeps source-page and text-block identity.
Downstream extraction can therefore store a compact evidence reference such as
``{"page": 1, "text_block_id": "p1-b3"}`` instead of copying text or
coordinates into every candidate field.
"""

from __future__ import annotations

import io
import json
import uuid
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any, Callable, Protocol, Sequence

from app.storage import PrivateObjectStorage, StorageError


class OCRServiceError(RuntimeError):
    """Raised when an OCR input cannot be processed."""


class OCRUnavailableError(OCRServiceError):
    """Raised when the optional PaddleOCR runtime is not installed."""


@dataclass(frozen=True)
class OCRPageInput:
    """A decoded raster page passed to an OCR implementation.

    ``image`` is intentionally typed as ``Any``: PaddleOCR accepts NumPy image
    arrays, while keeping NumPy out of the import path for callers and tests.
    """

    page: int
    image: Any


@dataclass(frozen=True)
class OCRTextBlock:
    """Recognized text and its source location on one page."""

    id: str
    text: str
    confidence: float | None
    bounding_box: tuple[tuple[float, float], ...]

    def evidence_reference(self, page: int) -> dict[str, int | str]:
        return {"page": page, "text_block_id": self.id}


@dataclass(frozen=True)
class OCRPage:
    """Normalized OCR output for an individual source page."""

    page: int
    source_method: str
    quality: float | None
    text_blocks: tuple[OCRTextBlock, ...]


@dataclass(frozen=True)
class OCRArtifact:
    """Portable, versioned OCR result stored in private object storage."""

    pages: tuple[OCRPage, ...]
    format_version: int = 1
    engine: str = "paddleocr"

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-safe artifact without losing evidence coordinates."""
        return asdict(self)

    def text_block_evidence(self) -> list[dict[str, int | str]]:
        """Return every valid page/text-block reference in the artifact."""
        return [
            block.evidence_reference(page.page)
            for page in self.pages
            for block in page.text_blocks
        ]


class OCRService(Protocol):
    """Provider-neutral OCR interface used by document processing."""

    def recognize(self, pages: Sequence[OCRPageInput]) -> OCRArtifact:
        """Recognize raster pages and return normalized blocks and evidence."""


class PaddleOCRService:
    """PaddleOCR adapter with lazy runtime initialization.

    Models are loaded on the first request, not when FastAPI imports the module.
    This keeps API startup deterministic and lets workers own OCR memory use.
    """

    def __init__(
        self,
        *,
        language: str = "en",
        use_angle_classification: bool = True,
        engine: Any | None = None,
        engine_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.language = language
        self.use_angle_classification = use_angle_classification
        self._engine = engine
        self._engine_factory = engine_factory

    def recognize(self, pages: Sequence[OCRPageInput]) -> OCRArtifact:
        if not pages:
            raise OCRServiceError("at least one page is required for OCR")
        if any(page.page < 1 for page in pages):
            raise OCRServiceError("OCR page numbers must start at one")
        if len({page.page for page in pages}) != len(pages):
            raise OCRServiceError("OCR page numbers must be unique")

        engine = self._get_engine()
        normalized_pages: list[OCRPage] = []
        for input_page in pages:
            try:
                result = engine.ocr(input_page.image, cls=self.use_angle_classification)
            except Exception as error:
                raise OCRServiceError(f"PaddleOCR failed on page {input_page.page}") from error
            normalized_pages.append(self._normalize_page(input_page.page, result))
        return OCRArtifact(pages=tuple(normalized_pages))

    def _get_engine(self) -> Any:
        if self._engine is not None:
            return self._engine
        if self._engine_factory is not None:
            self._engine = self._engine_factory()
            return self._engine
        try:
            from paddleocr import PaddleOCR
        except ImportError as error:
            raise OCRUnavailableError(
                "PaddleOCR is unavailable; install the OCR worker dependencies"
            ) from error
        try:
            self._engine = PaddleOCR(
                use_angle_cls=self.use_angle_classification,
                lang=self.language,
                show_log=False,
            )
        except Exception as error:
            raise OCRUnavailableError("PaddleOCR could not initialize") from error
        return self._engine

    @staticmethod
    def _normalize_page(page_number: int, result: Any) -> OCRPage:
        # PaddleOCR 2.x returns a one-item list for one input image.  Accept a
        # direct line list too, which makes the adapter tolerant of lightweight
        # test doubles and avoids coupling callers to Paddle's response shape.
        lines = result
        if (
            isinstance(result, (list, tuple))
            and len(result) == 1
            and isinstance(result[0], (list, tuple))
            and not PaddleOCRService._looks_like_line(result[0])
        ):
            lines = result[0]
        if lines is None:
            lines = []
        if not isinstance(lines, (list, tuple)):
            raise OCRServiceError(f"PaddleOCR returned an invalid result for page {page_number}")

        blocks: list[OCRTextBlock] = []
        confidences: list[float] = []
        for line in lines:
            parsed = PaddleOCRService._parse_line(line)
            if parsed is None:
                continue
            box, recognized_text, confidence = parsed
            text = recognized_text.strip()
            if not text:
                continue
            block_id = f"p{page_number}-b{len(blocks) + 1}"
            blocks.append(
                OCRTextBlock(
                    id=block_id,
                    text=text,
                    confidence=confidence,
                    bounding_box=box,
                )
            )
            if confidence is not None:
                confidences.append(confidence)

        quality = sum(confidences) / len(confidences) if confidences else None
        return OCRPage(
            page=page_number,
            source_method="paddleocr",
            quality=quality,
            text_blocks=tuple(blocks),
        )

    @staticmethod
    def _looks_like_line(value: Any) -> bool:
        """Identify Paddle's ``[polygon, (text, confidence)]`` line shape."""
        try:
            _, recognition = value
            text, _ = recognition
            return isinstance(text, str)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _parse_line(
        line: Any,
    ) -> tuple[tuple[tuple[float, float], ...], str, float | None] | None:
        try:
            raw_box, recognition = line
            text, raw_confidence = recognition
            box = tuple((float(point[0]), float(point[1])) for point in raw_box)
            if not box or not isinstance(text, str):
                return None
            confidence = float(raw_confidence) if raw_confidence is not None else None
            return box, text, confidence
        except (TypeError, ValueError, IndexError):
            return None


@lru_cache(maxsize=1)
def get_ocr_service() -> OCRService:
    """Return the worker-local default OCR provider.

    Keeping one adapter per process lets PaddleOCR retain its loaded models
    across jobs while preserving the provider-neutral ``OCRService`` boundary.
    """
    return PaddleOCRService()


class OCRArtifactStore:
    """Stores normalized OCR results under opaque, document-scoped keys."""

    def __init__(self, storage: PrivateObjectStorage) -> None:
        self._storage = storage

    def save(self, document_id: uuid.UUID | str, artifact: OCRArtifact) -> str:
        key = f"ocr/{document_id}/{uuid.uuid4()}.json"
        encoded = json.dumps(
            artifact.as_dict(), ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        try:
            self._storage.put(key, io.BytesIO(encoded))
        except StorageError:
            raise
        except Exception as error:
            raise StorageError("could not persist OCR artifact") from error
        return key


class DocumentOCRService:
    """Runs OCR for a private image/PDF document and saves its artifact."""

    def __init__(
        self,
        ocr: OCRService,
        artifact_store: OCRArtifactStore,
        *,
        max_pages: int = 10,
    ) -> None:
        if max_pages < 1:
            raise ValueError("max_pages must be at least one")
        self._ocr = ocr
        self._artifact_store = artifact_store
        self._max_pages = max_pages

    def process(
        self,
        *,
        document_id: uuid.UUID | str,
        storage_key: str,
        mime_type: str,
        storage: PrivateObjectStorage,
    ) -> tuple[str, OCRArtifact]:
        """Read a private original, OCR it, and return its stored artifact key."""
        try:
            with storage.open(storage_key) as source:
                content = source.read()
        except StorageError:
            raise
        except OSError as error:
            raise StorageError("could not read source document for OCR") from error

        artifact = self._ocr.recognize(self._raster_pages(content, mime_type))
        return self._artifact_store.save(document_id, artifact), artifact

    def _raster_pages(self, content: bytes, mime_type: str) -> tuple[OCRPageInput, ...]:
        if mime_type in {"image/jpeg", "image/png"}:
            return (OCRPageInput(page=1, image=self._decode_image(content)),)
        if mime_type == "application/pdf":
            return self._render_pdf(content)
        raise OCRServiceError(f"unsupported OCR MIME type: {mime_type}")

    @staticmethod
    def _decode_image(content: bytes) -> Any:
        try:
            import numpy as np
            from PIL import Image

            with Image.open(io.BytesIO(content)) as image:
                return np.asarray(image.convert("RGB"))
        except Exception as error:
            raise OCRServiceError("could not decode image for OCR") from error

    def _render_pdf(self, content: bytes) -> tuple[OCRPageInput, ...]:
        try:
            import numpy as np
            import pypdfium2 as pdfium

            pdf = pdfium.PdfDocument(content)
            try:
                page_count = len(pdf)
                if page_count == 0:
                    raise OCRServiceError("PDF has no pages")
                if page_count > self._max_pages:
                    raise OCRServiceError(
                        f"PDF has {page_count} pages; OCR limit is {self._max_pages}"
                    )
                pages = []
                for index in range(page_count):
                    page = pdf[index]
                    try:
                        bitmap = page.render(scale=2)
                        try:
                            pages.append(
                                OCRPageInput(
                                    page=index + 1,
                                    image=np.asarray(bitmap.to_pil().convert("RGB")),
                                )
                            )
                        finally:
                            bitmap.close()
                    finally:
                        page.close()
                return tuple(pages)
            finally:
                pdf.close()
        except OCRServiceError:
            raise
        except Exception as error:
            raise OCRServiceError("could not render PDF pages for OCR") from error
