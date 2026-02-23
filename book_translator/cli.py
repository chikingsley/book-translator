"""CLI entrypoints for the modular book translation pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .models import JudgeStrategy, OcrBackendKind, TranslationBackendKind, load_pipeline_config
from .pipeline import PipelineRunner

DEFAULT_CONFIG_TOML = """# book-translator pipeline config

[source]
input_path = "test-book-pdfs/sources/reich-ohne-raum.de.source.pdf"
source_language = "de"
target_language = "en"
translation_style = "literal"
translation_brief = "Prioritize source fidelity over modern paraphrase."
# human_reference_path = "test-book-pdfs/sources/reich-ohne-raum.en.legacy-working.md"

[output]
output_dir = "runs/book-translator"
write_manifest_json = true

[chaptering]
split_on_heading = true
heading_pattern = "(?m)^#{1,6}\\\\s+.+$"

[reconciliation]
min_ocr_backends = 3
min_translation_backends = 2
disagreement_marker_prefix = "[DIFF]"

[reconciliation.ocr_judge]
strategy = "majority-vote"
name = "ocr-majority"

[reconciliation.translation_judge]
strategy = "shell"
name = "opencode-glm5-judge"

[reconciliation.translation_judge.shell]
command = [
  "opencode",
  "run",
  "-m",
  "zai-coding-plan/glm-5",
  "--file",
  "{candidates_json_path}",
  "You are a strict translation judge. Use the attached JSON for phase={phase} chapter={chapter_id}. Reconcile the best output and return ONLY markdown."
]
output_mode = "stdout"
timeout_seconds = 2400
retry_attempts = 2
retry_backoff_seconds = 2.0

[[ocr_backends]]
name = "paddle-ocr"
kind = "shell"
enabled = true

[ocr_backends.shell]
command = ["bash", "-lc", "echo '# TODO: wire PaddleOCR for {input_path}'"]
output_mode = "stdout"
timeout_seconds = 1800
retry_attempts = 2
retry_backoff_seconds = 2.0

[[ocr_backends]]
name = "glm-ocr"
kind = "shell"
enabled = true

[ocr_backends.shell]
command = ["bash", "-lc", "echo '# TODO: wire GLM OCR for {input_path}'"]
output_mode = "stdout"
timeout_seconds = 1800
retry_attempts = 2
retry_backoff_seconds = 2.0

[[ocr_backends]]
name = "gemini-3-flash-preview"
kind = "shell"
enabled = true

[ocr_backends.shell]
command = ["bash", "-lc", "echo '# TODO: wire Gemini 3 Flash Preview OCR for {input_path}'"]
output_mode = "stdout"
timeout_seconds = 1800
retry_attempts = 2
retry_backoff_seconds = 2.0

[[translation_backends]]
name = "gemini-2.5-pro"
kind = "gemini"
enabled = true
model = "gemini-2.5-pro"
api_key_env = "GEMINI_API_KEY"
temperature = 0.2

[[translation_backends]]
name = "local-vllm"
kind = "openai-compatible"
enabled = true
model = "gpt-oss-120b"
base_url = "http://localhost:8000"
api_key_env = "OPENAI_COMPAT_API_KEY"
temperature = 0.2
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Book translator backend pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run OCR + translation pipeline")
    run_parser.add_argument("--config", type=Path, required=True, help="Path to pipeline TOML config")

    init_parser = subparsers.add_parser("init-config", help="Write a starter pipeline config")
    init_parser.add_argument(
        "--output",
        type=Path,
        default=Path("book-translator.toml"),
        help="Output path for starter config",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output file if it exists",
    )

    subparsers.add_parser("list-backends", help="Show supported backend kinds")

    return parser


def _run_pipeline(config_path: Path) -> int:
    config = load_pipeline_config(config_path)
    runner = PipelineRunner(config)
    manifest = runner.run()
    print(manifest.model_dump_json(indent=2))
    return 0


def _write_default_config(output_path: Path, force: bool) -> int:
    if output_path.exists() and not force:
        print(f"Refusing to overwrite existing file: {output_path}", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(DEFAULT_CONFIG_TOML, encoding="utf-8")
    print(f"Wrote starter config to {output_path}")
    return 0


def _list_backends() -> int:
    payload = {
        "ocr_backend_kinds": [kind.value for kind in OcrBackendKind],
        "translation_backend_kinds": [kind.value for kind in TranslationBackendKind],
        "judge_strategies": [kind.value for kind in JudgeStrategy],
    }
    print(json.dumps(payload, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return _run_pipeline(args.config)
    if args.command == "init-config":
        return _write_default_config(args.output, args.force)
    if args.command == "list-backends":
        return _list_backends()

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
