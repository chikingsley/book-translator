"""OCR backend interfaces and implementations."""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pymupdf

from .models import OcrBackendConfig, OcrBackendKind, ShellCommandConfig


@dataclass(slots=True)
class OcrRequest:
    """Input parameters for OCR execution."""

    input_path: Path
    output_dir: Path
    source_language: str


class OcrBackend(Protocol):
    """OCR backend protocol."""

    @property
    def name(self) -> str:
        """Stable backend name."""

    def run(self, request: OcrRequest) -> str:
        """Return markdown text extracted from request.input_path."""


class MarkdownFileBackend:
    """Pass-through backend for markdown sources."""

    def __init__(self, backend_name: str):
        self._name = backend_name

    @property
    def name(self) -> str:
        return self._name

    def run(self, request: OcrRequest) -> str:
        return request.input_path.read_text(encoding="utf-8")


class PyMuPdfNativeBackend:
    """Native text extraction backend using PyMuPDF."""

    def __init__(self, backend_name: str):
        self._name = backend_name

    @property
    def name(self) -> str:
        return self._name

    def run(self, request: OcrRequest) -> str:
        if request.input_path.suffix.lower() != ".pdf":
            raise ValueError(f"{self.name} only supports PDF input")

        doc = pymupdf.open(str(request.input_path))
        try:
            pages: list[str] = []
            for page_index in range(doc.page_count):
                page = doc[page_index]
                text = page.get_text()
                text = text.strip()
                page_number = page_index + 1
                pages.append(f"# Page {page_number}\n\n{text}" if text else f"# Page {page_number}\n")
            return "\n\n---\n\n".join(pages).strip() + "\n"
        finally:
            doc.close()


class ShellOcrBackend:
    """Shell command OCR backend for local/agent adapters."""

    def __init__(self, backend_name: str, shell: ShellCommandConfig):
        self._name = backend_name
        self._shell = shell

    @property
    def name(self) -> str:
        return self._name

    def run(self, request: OcrRequest) -> str:
        output_path = request.output_dir / f"{self.name}.md"
        command = self._format_command(
            request=request,
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
                return text.strip() + "\n"

            if attempt < attempts:
                time.sleep(self._shell.retry_backoff_seconds * attempt)

        stderr = result.stderr.strip() if result.stderr else ""
        raise RuntimeError(
            f"OCR backend '{self.name}' failed after {attempts} attempts: "
            f"exit={result.returncode} stderr={stderr or '<empty>'}"
        )

    def _resolve_output_text(self, result: subprocess.CompletedProcess[str], output_path: Path) -> str:
        if self._shell.output_mode == "stdout":
            return result.stdout
        if not output_path.exists():
            return ""
        return output_path.read_text(encoding="utf-8")

    def _format_command(self, request: OcrRequest, output_path: Path) -> list[str]:
        formatted: list[str] = []
        for token in self._shell.command:
            formatted.append(
                token.format(
                    input_path=request.input_path,
                    output_path=output_path,
                    language=request.source_language,
                )
            )
        return formatted


def build_ocr_backends(configs: list[OcrBackendConfig]) -> list[OcrBackend]:
    """Instantiate enabled OCR backends from config."""
    backends: list[OcrBackend] = []
    for backend in configs:
        if not backend.enabled:
            continue

        if backend.kind == OcrBackendKind.markdown_file:
            backends.append(MarkdownFileBackend(backend.name))
        elif backend.kind == OcrBackendKind.pymupdf_native:
            backends.append(PyMuPdfNativeBackend(backend.name))
        elif backend.kind == OcrBackendKind.shell:
            if backend.shell is None:
                raise ValueError(f"shell config missing for OCR backend '{backend.name}'")
            backends.append(ShellOcrBackend(backend.name, backend.shell))
        else:
            raise ValueError(f"unsupported OCR backend kind: {backend.kind}")

    if not backends:
        raise ValueError("no enabled OCR backends")

    return backends
