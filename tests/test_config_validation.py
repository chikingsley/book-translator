"""Tests for pipeline config validation."""

from pathlib import Path

import pytest

from book_translator.models import (
    OcrBackendConfig,
    OcrBackendKind,
    PipelineConfig,
    SourceConfig,
    TranslationBackendConfig,
    TranslationBackendKind,
)


def test_pipeline_requires_two_ocr_backends() -> None:
    """Reject configs that do not meet OCR backend minimums."""
    with pytest.raises(ValueError):
        PipelineConfig(
            source=SourceConfig(input_path=Path("book.pdf")),
            ocr_backends=[
                OcrBackendConfig(name="one", kind=OcrBackendKind.pymupdf_native),
            ],
            translation_backends=[
                TranslationBackendConfig(
                    name="t1",
                    kind=TranslationBackendKind.openai_compatible,
                    model="gpt-oss",
                    base_url="http://localhost:8000",
                ),
                TranslationBackendConfig(
                    name="t2",
                    kind=TranslationBackendKind.openai_compatible,
                    model="gpt-oss",
                    base_url="http://localhost:8001",
                ),
            ],
        )
