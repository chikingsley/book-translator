"""End-to-end orchestration for OCR + translation + reconciliation."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from .chaptering import split_markdown_into_chapters
from .judging import JudgeBackend, JudgeRequest, build_judge_backend
from .models import (
    BackendRunRecord,
    ChapterRunRecord,
    PipelineConfig,
    PipelineRunManifest,
    utc_timestamp,
)
from .ocr_backends import OcrRequest, build_ocr_backends
from .reconciliation import similarity_score
from .translation_backends import TranslationRequest, build_translation_backends


class PipelineRunner:
    """Run the configured translation pipeline and persist artifacts."""

    def __init__(self, config: PipelineConfig):
        self._config = config

    def run(self) -> PipelineRunManifest:
        run_id = uuid.uuid4().hex[:12]
        output_dir = self._resolve_output_dir(run_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        ocr_dir = output_dir / "ocr"
        chapters_dir = output_dir / "chapters"
        translations_dir = output_dir / "translations"
        for directory in (ocr_dir, chapters_dir, translations_dir):
            directory.mkdir(parents=True, exist_ok=True)

        ocr_judge = build_judge_backend(self._config.reconciliation.ocr_judge, default_name="ocr-majority")
        translation_judge = build_judge_backend(
            self._config.reconciliation.translation_judge,
            default_name="translation-majority",
        )

        ocr_text, ocr_records, ocr_disagreement_count = self._run_ocr_phase(ocr_dir, ocr_judge)
        chapters = split_markdown_into_chapters(ocr_text, self._config.chaptering)
        chapter_records: list[ChapterRunRecord] = []
        final_chapter_texts: list[str] = []
        translation_backends = build_translation_backends(self._config.translation_backends)

        for chapter in chapters:
            chapter_source_path = chapters_dir / f"{chapter.chapter_id}_source.md"
            chapter_source_path.write_text(chapter.content.strip() + "\n", encoding="utf-8")

            chapter_translation_dir = translations_dir / chapter.chapter_id
            chapter_translation_dir.mkdir(parents=True, exist_ok=True)

            translation_variants: dict[str, str] = {}
            translation_variant_artifacts: dict[str, Path] = {}
            translation_records: list[BackendRunRecord] = []

            for backend in translation_backends:
                started_at = time.perf_counter()
                translated_text = backend.translate(
                    TranslationRequest(
                        chapter_id=chapter.chapter_id,
                        chapter_title=chapter.title,
                        source_text=chapter.content,
                        source_language=self._config.source.source_language,
                        target_language=self._config.source.target_language,
                        translation_style=self._config.source.translation_style,
                        translation_brief=self._config.source.translation_brief,
                        output_dir=chapter_translation_dir,
                    )
                )
                duration = time.perf_counter() - started_at

                artifact_path = chapter_translation_dir / f"{backend.name}.md"
                artifact_path.write_text(translated_text, encoding="utf-8")
                translation_variants[backend.name] = translated_text
                translation_variant_artifacts[backend.name] = artifact_path
                translation_records.append(
                    BackendRunRecord(
                        backend=backend.name,
                        artifact_path=self._relative_artifact_path(artifact_path, output_dir),
                        duration_seconds=duration,
                    )
                )

            chapter_consensus = translation_judge.judge(
                JudgeRequest(
                    phase="translation",
                    chapter_id=chapter.chapter_id,
                    chapter_title=chapter.title,
                    variants=translation_variants,
                    variant_artifacts=translation_variant_artifacts,
                    output_dir=chapter_translation_dir,
                    disagreement_marker_prefix=self._config.reconciliation.disagreement_marker_prefix,
                    source_language=self._config.source.source_language,
                    target_language=self._config.source.target_language,
                    translation_style=self._config.source.translation_style,
                )
            )
            chapter_reconciled_path = chapters_dir / f"{chapter.chapter_id}_translated.md"
            chapter_reconciled_path.write_text(chapter_consensus.text, encoding="utf-8")

            chapter_records.append(
                ChapterRunRecord(
                    chapter_id=chapter.chapter_id,
                    title=chapter.title,
                    source_artifact=self._relative_artifact_path(chapter_source_path, output_dir),
                    translations=translation_records,
                    reconciled_artifact=self._relative_artifact_path(chapter_reconciled_path, output_dir),
                    disagreement_count=chapter_consensus.disagreement_count,
                )
            )
            final_chapter_texts.append(chapter_consensus.text.rstrip())

        final_book_text = "\n\n---\n\n".join(final_chapter_texts).strip() + "\n"
        final_book_path = output_dir / "final-book.md"
        final_book_path.write_text(final_book_text, encoding="utf-8")

        reference_similarity: float | None = None
        reference_path = self._config.source.human_reference_path
        if reference_path and reference_path.exists():
            reference_text = reference_path.read_text(encoding="utf-8")
            reference_similarity = similarity_score(final_book_text, reference_text)

        manifest = PipelineRunManifest(
            run_id=run_id,
            created_at=utc_timestamp(),
            input_path=str(self._config.source.input_path),
            output_dir=str(output_dir),
            ocr_judge_backend=ocr_judge.name,
            translation_judge_backend=translation_judge.name,
            ocr_runs=ocr_records,
            ocr_reconciled_artifact=self._relative_artifact_path(ocr_dir / "reconciled.md", output_dir),
            ocr_disagreement_count=ocr_disagreement_count,
            chapters=chapter_records,
            final_book_artifact=self._relative_artifact_path(final_book_path, output_dir),
            reference_similarity=reference_similarity,
        )

        if self._config.output.write_manifest_json:
            manifest_path = output_dir / "manifest.json"
            manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

        return manifest

    def _run_ocr_phase(
        self,
        ocr_dir: Path,
        ocr_judge: JudgeBackend,
    ) -> tuple[str, list[BackendRunRecord], int]:
        ocr_backends = build_ocr_backends(self._config.ocr_backends)

        variants: dict[str, str] = {}
        variant_artifacts: dict[str, Path] = {}
        records: list[BackendRunRecord] = []

        for backend in ocr_backends:
            started_at = time.perf_counter()
            extracted = backend.run(
                OcrRequest(
                    input_path=self._config.source.input_path,
                    output_dir=ocr_dir,
                    source_language=self._config.source.source_language,
                )
            )
            duration = time.perf_counter() - started_at

            artifact_path = ocr_dir / f"{backend.name}.md"
            artifact_path.write_text(extracted, encoding="utf-8")
            variants[backend.name] = extracted
            variant_artifacts[backend.name] = artifact_path
            records.append(
                BackendRunRecord(
                    backend=backend.name,
                    artifact_path=self._relative_artifact_path(artifact_path, ocr_dir.parent),
                    duration_seconds=duration,
                )
            )

        reconciled = ocr_judge.judge(
            JudgeRequest(
                phase="ocr",
                chapter_id="000",
                chapter_title="OCR Consensus",
                variants=variants,
                variant_artifacts=variant_artifacts,
                output_dir=ocr_dir,
                disagreement_marker_prefix=self._config.reconciliation.disagreement_marker_prefix,
                source_language=self._config.source.source_language,
                target_language=self._config.source.target_language,
                translation_style=self._config.source.translation_style,
            )
        )
        reconciled_path = ocr_dir / "reconciled.md"
        reconciled_path.write_text(reconciled.text, encoding="utf-8")

        disagreements_path = ocr_dir / "reconciliation-summary.json"
        disagreements_path.write_text(
            json.dumps(
                {
                    "backend_count": len(variants),
                    "judge_backend": ocr_judge.name,
                    "disagreement_count": reconciled.disagreement_count,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        return reconciled.text, records, reconciled.disagreement_count

    def _resolve_output_dir(self, run_id: str) -> Path:
        base = self._config.output.output_dir
        if not base.is_absolute():
            base = Path.cwd() / base
        return base / run_id

    @staticmethod
    def _relative_artifact_path(path: Path, run_root: Path) -> str:
        try:
            return str(path.relative_to(run_root))
        except ValueError:
            return str(path)
