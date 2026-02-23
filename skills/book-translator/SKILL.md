---
name: book-translator
description: >-
  Run a chapter-by-chapter book translation workflow with OCR and translation ensembles.
  Use when translating long-form books where at least two OCR backends and at least two
  translation backends must run, then be reconciled into a final auditable output.
---

# Book Translator

This skill runs a reproducible backend pipeline for translating books.

## Use this skill when

- Input is a PDF or markdown source for a full book
- OCR should run through multiple backends
- Translation should run through multiple models/backends
- You need chapter-level artifacts, disagreement traces, and a final manifest

## Workflow

1. Ensure a config exists:

```bash
uv run book-translator init-config --output book-translator.toml
```

2. Update `book-translator.toml` with actual OCR and translation backends.
- Keep at least 2 enabled OCR backends.
- Keep at least 2 enabled translation backends.
- Prefer 3 backends for stronger reconciliation.
- Configure `reconciliation.translation_judge` as `strategy = "shell"` when using terminal-agent judging.
- Default judge model: `opencode run -m zai-coding-plan/glm-5`.

3. Run the pipeline:

```bash
uv run book-translator run --config book-translator.toml
```

4. Inspect outputs under `runs/book-translator/<run_id>/`:
- `ocr/*.md` for per-backend OCR outputs
- `ocr/reconciled.md` for consensus source
- `chapters/*_source.md` for split source chapters
- `translations/<chapter_id>/*.md` for per-backend chapter translations
- `chapters/*_translated.md` for reconciled chapter outputs
- `final-book.md` for assembled final translation
- `manifest.json` for run metadata and auditability

## Notes

- Shell backends are intended for local CLI agents and VLLM wrappers.
- Shell judges are intended for terminal-agent reconciliation (`opencode run` or equivalent).
- Gemini and OpenAI-compatible backends are supported for translation.
- Add `source.human_reference_path` in config to score similarity against a human reference draft.
