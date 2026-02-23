"""Judge backends used to reconcile OCR and translation candidates."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from .models import JudgeConfig, JudgeStrategy, ShellCommandConfig
from .reconciliation import reconcile_text_variants


@dataclass(slots=True)
class JudgeRequest:
    """Input payload for chapter/phase reconciliation."""

    phase: Literal["ocr", "translation"]
    chapter_id: str
    chapter_title: str
    variants: dict[str, str]
    variant_artifacts: dict[str, Path]
    output_dir: Path
    disagreement_marker_prefix: str
    source_language: str
    target_language: str
    translation_style: str


@dataclass(slots=True)
class JudgeResult:
    """Final judged markdown and disagreement metadata."""

    text: str
    disagreement_count: int


class JudgeBackend(Protocol):
    """Judge backend protocol."""

    @property
    def name(self) -> str:
        """Stable backend name."""

    def judge(self, request: JudgeRequest) -> JudgeResult:
        """Return judged markdown for the given request."""


class MajorityVoteJudge:
    """Deterministic majority-vote judge."""

    def __init__(self, backend_name: str):
        self._name = backend_name

    @property
    def name(self) -> str:
        return self._name

    def judge(self, request: JudgeRequest) -> JudgeResult:
        result = reconcile_text_variants(
            request.variants,
            marker_prefix=request.disagreement_marker_prefix,
        )
        return JudgeResult(text=result.text, disagreement_count=result.disagreement_count)


class ShellJudge:
    """Shell-driven judge backend, suitable for terminal agents."""

    def __init__(self, backend_name: str, shell: ShellCommandConfig):
        self._name = backend_name
        self._shell = shell

    @property
    def name(self) -> str:
        return self._name

    def judge(self, request: JudgeRequest) -> JudgeResult:
        output_path = request.output_dir / f"{request.phase}-{request.chapter_id}-judge-output.md"
        candidates_json_path = request.output_dir / f"{request.phase}-{request.chapter_id}-judge-input.json"
        candidates_json_path.write_text(
            json.dumps(
                {
                    "phase": request.phase,
                    "chapter_id": request.chapter_id,
                    "chapter_title": request.chapter_title,
                    "source_language": request.source_language,
                    "target_language": request.target_language,
                    "translation_style": request.translation_style,
                    "disagreement_marker_prefix": request.disagreement_marker_prefix,
                    "candidates": [
                        {
                            "backend": backend,
                            "artifact_path": str(request.variant_artifacts[backend]),
                            "text": request.variants[backend],
                        }
                        for backend in sorted(request.variants)
                    ],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        command = self._format_command(
            request=request,
            candidates_json_path=candidates_json_path,
            output_path=output_path,
        )
        attempts = self._shell.retry_attempts
        for attempt in range(1, attempts + 1):
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self._shell.timeout_seconds,
                env=({**os.environ, **self._shell.env} if self._shell.env else None),
            )
            text = self._resolve_output_text(result, output_path)
            if result.returncode == 0 and text.strip():
                return JudgeResult(
                    text=text.strip() + "\n",
                    disagreement_count=_estimate_disagreement_count(request),
                )
            if attempt < attempts:
                time.sleep(self._shell.retry_backoff_seconds * attempt)

        stderr = result.stderr.strip() if result.stderr else ""
        raise RuntimeError(
            f"Judge backend '{self.name}' failed after {attempts} attempts: "
            f"exit={result.returncode} stderr={stderr or '<empty>'}"
        )

    def _resolve_output_text(self, result: subprocess.CompletedProcess[str], output_path: Path) -> str:
        if self._shell.output_mode == "stdout":
            return result.stdout
        if not output_path.exists():
            return ""
        return output_path.read_text(encoding="utf-8")

    def _format_command(
        self,
        request: JudgeRequest,
        candidates_json_path: Path,
        output_path: Path,
    ) -> list[str]:
        return [
            token.format(
                phase=request.phase,
                chapter_id=request.chapter_id,
                chapter_title=request.chapter_title,
                candidates_json_path=candidates_json_path,
                output_path=output_path,
                source_language=request.source_language,
                target_language=request.target_language,
                translation_style=request.translation_style,
                disagreement_marker_prefix=request.disagreement_marker_prefix,
            )
            for token in self._shell.command
        ]


def build_judge_backend(config: JudgeConfig, default_name: str) -> JudgeBackend:
    """Build a judge backend from config."""
    name = config.name or default_name
    if config.strategy == JudgeStrategy.majority_vote:
        return MajorityVoteJudge(name)
    if config.strategy == JudgeStrategy.shell:
        if config.shell is None:
            raise ValueError(f"shell config missing for judge backend '{name}'")
        return ShellJudge(name, config.shell)
    raise ValueError(f"unsupported judge strategy: {config.strategy}")


def _estimate_disagreement_count(request: JudgeRequest) -> int:
    """Estimate disagreement count from raw variants for reporting."""
    return reconcile_text_variants(
        request.variants,
        marker_prefix=request.disagreement_marker_prefix,
    ).disagreement_count
