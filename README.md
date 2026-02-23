# book-translator

Backend-first OCR and translation pipeline for long-form books.

## Current direction

This repository now targets a modular architecture with two explicit phases:

1. OCR ensemble phase
- Run at least 2 OCR backends (preferably 3).
- Persist each backend output.
- Reconcile disagreements into a single canonical source markdown.

2. Translation ensemble phase
- Split reconciled source into chapters.
- Run at least 2 translation backends per chapter.
- Reconcile disagreements into final chapter outputs, optionally via a shell judge.

The pipeline writes machine-readable run manifests so every run is auditable and reproducible.

## CLI

```bash
uv run book-translator list-backends
uv run book-translator init-config --output book-translator.toml
uv run book-translator run --config book-translator.toml
```

EPUB export:

```bash
uv run create-ebook runs/book-translator/<run_id>/final-book.md
```

## Tooling

```bash
uv run ruff check .
uv run ty check
uv run pytest -q
```

## Config model

Primary config sections:

- `[source]`: input path, source/target language, style, optional human reference
- `[ocr_backends]`: backend list (`markdown-file`, `pymupdf-native`, `shell`)
- `[translation_backends]`: backend list (`shell`, `gemini`, `openai-compatible`)
- `[reconciliation]`: minimum backend counts, disagreement marker policy, and judge strategy
- `[output]`: run artifact destination

Generate a starter config with:

```bash
uv run book-translator init-config
```

The generated starter config now defaults OCR to:

- `paddle-ocr`
- `glm-ocr`
- `gemini-3-flash-preview`

And sets translation judging to `opencode run -m zai-coding-plan/glm-5`.

Check local `opencode` model availability with:

```bash
opencode models | rg 'glm-5|flash|gemini'
```

## About legacy scripts

The numbered scripts under `book_translator/` and `book_translator/archive/` are retained for reference/history.
The supported forward path is `book_translator.cli` and the config-driven pipeline.
