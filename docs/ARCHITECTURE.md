# Backend Architecture (Target State)

## Core principle

Treat OCR and translation as two separate ensemble phases.

1. OCR ensemble
- Run N OCR backends (`N >= 2`, preferred `N >= 3`).
- Persist each backend output.
- Reconcile into a canonical source text.

2. Translation ensemble
- Split canonical source into chapters.
- Run N translation backends per chapter (`N >= 2`, preferred `N >= 3`).
- Reconcile each chapter into a final translation chapter using either:
  - deterministic majority vote, or
  - a terminal-agent shell judge (for example `opencode run`).

3. Evaluation
- Optionally compare final output against a human reference draft.
- Keep score in run manifest.

## Why this structure

- Prevents one model/backend from being a single point of failure.
- Makes disagreements explicit and auditable.
- Supports local model + hosted model combinations.
- Works naturally with agentic workflows (shell adapters, local CLIs, VLLM endpoints).

## Pipeline boundaries

- OCR backends implement `book_translator.ocr_backends.OcrBackend`.
- Translation backends implement `book_translator.translation_backends.TranslationBackend`.
- Reconciliation is centralized in `book_translator.reconciliation`.
- Judge execution is centralized in `book_translator.judging`.
- Orchestration lives in `book_translator.pipeline.PipelineRunner`.

## Artifact contract

Each run writes:

- per-backend OCR output
- reconciled OCR output
- chapter source files
- per-backend chapter translations
- reconciled chapter translations
- final assembled book
- machine-readable `manifest.json`
