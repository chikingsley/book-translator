"""Typed configuration and manifest models for the translation pipeline."""

from __future__ import annotations

import tomllib
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class OcrBackendKind(StrEnum):
    """Supported OCR backend kinds."""

    markdown_file = "markdown-file"
    pymupdf_native = "pymupdf-native"
    shell = "shell"


class TranslationBackendKind(StrEnum):
    """Supported translation backend kinds."""

    shell = "shell"
    gemini = "gemini"
    openai_compatible = "openai-compatible"


class JudgeStrategy(StrEnum):
    """Supported reconciliation judge strategies."""

    majority_vote = "majority-vote"
    shell = "shell"


class ShellCommandConfig(BaseModel):
    """Configuration for shell-based adapters."""

    model_config = ConfigDict(extra="forbid")

    command: list[str] = Field(
        ...,
        description=(
            "Command template tokens. Supports placeholders like "
            "{input_path}, {output_path}, {language}, {source_language}, {target_language}, "
            "{chapter_id}, {phase}, and {candidates_json_path}."
        ),
    )
    timeout_seconds: int = Field(default=1800, ge=1, le=86400)
    output_mode: Literal["stdout", "file"] = "stdout"
    env: dict[str, str] = Field(default_factory=dict)
    retry_attempts: int = Field(default=1, ge=1, le=10)
    retry_backoff_seconds: float = Field(default=1.5, ge=0.0, le=300.0)


class JudgeConfig(BaseModel):
    """Reconciliation judge configuration."""

    model_config = ConfigDict(extra="forbid")

    strategy: JudgeStrategy = JudgeStrategy.majority_vote
    name: str | None = None
    shell: ShellCommandConfig | None = None

    @model_validator(mode="after")
    def validate_shell(self) -> JudgeConfig:
        """Require shell config when shell strategy is selected."""
        if self.strategy == JudgeStrategy.shell and self.shell is None:
            raise ValueError("shell config is required when judge strategy is 'shell'")
        return self


class OcrBackendConfig(BaseModel):
    """OCR backend configuration."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    kind: OcrBackendKind
    enabled: bool = True
    language: str | None = None
    shell: ShellCommandConfig | None = None

    @model_validator(mode="after")
    def validate_shell(self) -> OcrBackendConfig:
        """Require shell config for shell OCR backends."""
        if self.kind == OcrBackendKind.shell and self.shell is None:
            raise ValueError("shell config is required when OCR kind is 'shell'")
        return self


class TranslationBackendConfig(BaseModel):
    """Translation backend configuration."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    kind: TranslationBackendKind
    enabled: bool = True
    model: str | None = None
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    api_key_env: str | None = None
    base_url: str | None = None
    shell: ShellCommandConfig | None = None

    @model_validator(mode="after")
    def validate_backend_fields(self) -> TranslationBackendConfig:
        """Normalize and validate translation backend-specific fields."""
        if self.kind == TranslationBackendKind.shell and self.shell is None:
            raise ValueError("shell config is required when translation kind is 'shell'")
        if self.kind == TranslationBackendKind.gemini and not self.model:
            self.model = "gemini-2.5-pro"
        if self.kind == TranslationBackendKind.openai_compatible:
            if not self.model:
                raise ValueError("model is required for 'openai-compatible' translation backends")
            if not self.base_url:
                raise ValueError("base_url is required for 'openai-compatible' translation backends")
        return self


class SourceConfig(BaseModel):
    """Input source and language settings."""

    model_config = ConfigDict(extra="forbid")

    input_path: Path
    source_language: str = "de"
    target_language: str = "en"
    translation_style: Literal["literal", "literary", "scholarly"] = "literal"
    translation_brief: str | None = None
    human_reference_path: Path | None = None


class OutputConfig(BaseModel):
    """Output artifact settings."""

    model_config = ConfigDict(extra="forbid")

    output_dir: Path = Path("runs/latest")
    write_manifest_json: bool = True


class ChapteringConfig(BaseModel):
    """Chapter splitting configuration."""

    model_config = ConfigDict(extra="forbid")

    split_on_heading: bool = True
    heading_pattern: str = r"(?m)^#{1,6}\s+.+$"


class ReconciliationConfig(BaseModel):
    """Consensus/reconciliation policy."""

    model_config = ConfigDict(extra="forbid")

    min_ocr_backends: int = Field(default=2, ge=2, le=10)
    min_translation_backends: int = Field(default=2, ge=2, le=10)
    disagreement_marker_prefix: str = "[DIFF]"
    ocr_judge: JudgeConfig = Field(default_factory=JudgeConfig)
    translation_judge: JudgeConfig = Field(default_factory=JudgeConfig)


class PipelineConfig(BaseModel):
    """Top-level pipeline configuration."""

    model_config = ConfigDict(extra="forbid")

    source: SourceConfig
    output: OutputConfig = Field(default_factory=OutputConfig)
    chaptering: ChapteringConfig = Field(default_factory=ChapteringConfig)
    reconciliation: ReconciliationConfig = Field(default_factory=ReconciliationConfig)
    ocr_backends: list[OcrBackendConfig]
    translation_backends: list[TranslationBackendConfig]

    @model_validator(mode="after")
    def validate_backend_counts(self) -> PipelineConfig:
        """Enforce minimum enabled backend counts for each phase."""
        enabled_ocr = [b for b in self.ocr_backends if b.enabled]
        enabled_translation = [b for b in self.translation_backends if b.enabled]

        if len(enabled_ocr) < self.reconciliation.min_ocr_backends:
            raise ValueError(
                "enabled OCR backends are fewer than reconciliation.min_ocr_backends "
                f"({len(enabled_ocr)} < {self.reconciliation.min_ocr_backends})"
            )

        if len(enabled_translation) < self.reconciliation.min_translation_backends:
            raise ValueError(
                "enabled translation backends are fewer than reconciliation.min_translation_backends "
                f"({len(enabled_translation)} < {self.reconciliation.min_translation_backends})"
            )

        return self


class BackendRunRecord(BaseModel):
    """Metadata for a single backend run."""

    model_config = ConfigDict(extra="forbid")

    backend: str
    artifact_path: str
    duration_seconds: float


class ChapterRunRecord(BaseModel):
    """Metadata for one translated chapter."""

    model_config = ConfigDict(extra="forbid")

    chapter_id: str
    title: str
    source_artifact: str
    translations: list[BackendRunRecord]
    reconciled_artifact: str
    disagreement_count: int


class PipelineRunManifest(BaseModel):
    """Machine-readable manifest for a pipeline run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    created_at: str
    input_path: str
    output_dir: str
    ocr_judge_backend: str
    translation_judge_backend: str
    ocr_runs: list[BackendRunRecord]
    ocr_reconciled_artifact: str
    ocr_disagreement_count: int
    chapters: list[ChapterRunRecord]
    final_book_artifact: str
    reference_similarity: float | None = None


def load_pipeline_config(path: Path) -> PipelineConfig:
    """Load pipeline configuration from a TOML file."""
    with path.open("rb") as config_file:
        payload = tomllib.load(config_file)

    try:
        return PipelineConfig.model_validate(payload)
    except ValidationError as error:
        raise ValueError(f"invalid pipeline config at {path}: {error}") from error


def build_default_config() -> PipelineConfig:
    """Create a sane default config for quick starts."""
    return PipelineConfig(
        source=SourceConfig(input_path=Path("test-book-pdfs/sources/reich-ohne-raum.de.source.pdf")),
        reconciliation=ReconciliationConfig(
            min_ocr_backends=3,
            min_translation_backends=2,
            translation_judge=JudgeConfig(
                strategy=JudgeStrategy.shell,
                name="opencode-glm5-judge",
                shell=ShellCommandConfig(
                    command=[
                        "opencode",
                        "run",
                        "-m",
                        "zai-coding-plan/glm-5",
                        "--file",
                        "{candidates_json_path}",
                        "You are a rigorous chapter translation judge. "
                        "Use the attached JSON as the full input source for phase={phase}, chapter={chapter_id}. "
                        "Select and reconcile the best lines into a single faithful markdown chapter. "
                        "Preserve headings, paragraph boundaries, and notes. "
                        "Output ONLY the final markdown with no explanation.",
                    ],
                    output_mode="stdout",
                    timeout_seconds=1800,
                    retry_attempts=2,
                    retry_backoff_seconds=2.0,
                ),
            ),
        ),
        ocr_backends=[
            OcrBackendConfig(
                name="paddle-ocr",
                kind=OcrBackendKind.shell,
                shell=ShellCommandConfig(
                    command=[
                        "bash",
                        "-lc",
                        "echo '# TODO: wire paddle OCR for {input_path}'",
                    ]
                ),
            ),
            OcrBackendConfig(
                name="glm-ocr",
                kind=OcrBackendKind.shell,
                shell=ShellCommandConfig(
                    command=[
                        "bash",
                        "-lc",
                        "echo '# TODO: wire GLM OCR for {input_path}'",
                    ]
                ),
            ),
            OcrBackendConfig(
                name="gemini-3-flash-preview",
                kind=OcrBackendKind.shell,
                shell=ShellCommandConfig(
                    command=[
                        "bash",
                        "-lc",
                        "echo '# TODO: wire Gemini 3 Flash Preview OCR for {input_path}'",
                    ]
                ),
            ),
        ],
        translation_backends=[
            TranslationBackendConfig(
                name="gemini-2.5-pro",
                kind=TranslationBackendKind.gemini,
                model="gemini-2.5-pro",
            ),
            TranslationBackendConfig(
                name="local-vllm",
                kind=TranslationBackendKind.openai_compatible,
                model="gpt-oss-120b",
                base_url="http://localhost:8000",
                api_key_env="OPENAI_COMPAT_API_KEY",
            ),
        ],
    )


def default_config_payload() -> dict[str, Any]:
    """Create a TOML-serializable default payload."""
    config = build_default_config()
    return config.model_dump(mode="json")


def utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp for run manifests."""
    return datetime.now(UTC).isoformat()
