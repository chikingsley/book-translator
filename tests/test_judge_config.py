"""Tests for reconciliation judge configuration."""

from pathlib import Path

import pytest

from book_translator.models import (
    JudgeConfig,
    JudgeStrategy,
    OcrBackendConfig,
    OcrBackendKind,
    PipelineConfig,
    ReconciliationConfig,
    ShellCommandConfig,
    SourceConfig,
    TranslationBackendConfig,
    TranslationBackendKind,
)


def test_shell_judge_requires_shell_config() -> None:
    """Require shell command config for shell-based judge strategies."""
    with pytest.raises(ValueError):
        JudgeConfig(strategy=JudgeStrategy.shell)


def test_pipeline_accepts_shell_translation_judge() -> None:
    """Allow pipeline config with shell translation judge enabled."""
    config = PipelineConfig(
        source=SourceConfig(input_path=Path("book.pdf")),
        ocr_backends=[
            OcrBackendConfig(name="ocr-a", kind=OcrBackendKind.markdown_file),
            OcrBackendConfig(name="ocr-b", kind=OcrBackendKind.markdown_file),
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
        reconciliation=ReconciliationConfig(
            translation_judge=JudgeConfig(
                strategy=JudgeStrategy.shell,
                shell=ShellCommandConfig(
                    command=["echo", "ok"],
                    output_mode="stdout",
                ),
            )
        ),
    )

    assert config.reconciliation.translation_judge.strategy == JudgeStrategy.shell
    assert isinstance(config.reconciliation.translation_judge.shell, ShellCommandConfig)
