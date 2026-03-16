# book-translator

Composable OCR + translation pipeline for long-form books.

## Architecture

Two-phase ensemble pipeline:
1. **OCR phase**: Run 2-3 backends, reconcile into canonical source markdown
2. **Translation phase**: Split into chapters, run 2-3 translation backends per chapter, reconcile via judge

## Key Modules

| Module | Purpose |
|--------|---------|
| `cli.py` | Entry point (`book-translator` command) |
| `pipeline.py` | Config-driven orchestration |
| `ocr_backends.py` | OCR backend implementations (Gemini, Mistral, Tesseract, shell) |
| `translation_backends.py` | Translation backend implementations |
| `chaptering.py` | Chapter splitting logic |
| `reconciliation.py` | Multi-backend disagreement resolution |
| `judging.py` | Judge strategy for picking best translation |
| `create_ebook.py` | EPUB export from final markdown |
| `models.py` | Pydantic config and data models |

## Commands

```bash
uv run book-translator list-backends
uv run book-translator init-config --output book-translator.toml
uv run book-translator run --config book-translator.toml
uv run create-ebook runs/book-translator/<run_id>/final-book.md
```

## Dev

```bash
uv run ruff check .
uv run ty check
uv run pytest -q
```
