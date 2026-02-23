"""Translation backend interfaces and implementations."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import requests
from google import genai

from .models import ShellCommandConfig, TranslationBackendConfig, TranslationBackendKind


@dataclass(slots=True)
class TranslationRequest:
    """Input parameters for a translation backend."""

    chapter_id: str
    chapter_title: str
    source_text: str
    source_language: str
    target_language: str
    translation_style: str
    translation_brief: str | None
    output_dir: Path


class TranslationBackend(Protocol):
    """Translation backend protocol."""

    @property
    def name(self) -> str:
        """Stable backend name."""

    def translate(self, request: TranslationRequest) -> str:
        """Return translated chapter markdown."""


class ShellTranslationBackend:
    """Shell command translation backend for local VLLM/agents."""

    def __init__(self, backend_name: str, shell: ShellCommandConfig):
        self._name = backend_name
        self._shell = shell

    @property
    def name(self) -> str:
        return self._name

    def translate(self, request: TranslationRequest) -> str:
        output_path = request.output_dir / f"{self.name}.md"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as temp_file:
            temp_file.write(request.source_text)
            temp_input_path = Path(temp_file.name)

        try:
            command = self._format_command(request, temp_input_path, output_path)
            env = {**os.environ, **self._shell.env}
            attempts = self._shell.retry_attempts
            for attempt in range(1, attempts + 1):
                result = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=self._shell.timeout_seconds,
                    env=env,
                )
                text = self._resolve_output_text(result, output_path)
                if result.returncode == 0 and text.strip():
                    return text.strip() + "\n"
                if attempt < attempts:
                    time.sleep(self._shell.retry_backoff_seconds * attempt)

            stderr = result.stderr.strip() if result.stderr else ""
            raise RuntimeError(
                f"Translation backend '{self.name}' failed after {attempts} attempts: "
                f"exit={result.returncode} stderr={stderr or '<empty>'}"
            )
        finally:
            temp_input_path.unlink(missing_ok=True)

    def _resolve_output_text(self, result: subprocess.CompletedProcess[str], output_path: Path) -> str:
        if self._shell.output_mode == "stdout":
            return result.stdout
        if not output_path.exists():
            return ""
        return output_path.read_text(encoding="utf-8")

    def _format_command(
        self,
        request: TranslationRequest,
        input_path: Path,
        output_path: Path,
    ) -> list[str]:
        command: list[str] = []
        for token in self._shell.command:
            command.append(
                token.format(
                    chapter_id=request.chapter_id,
                    chapter_title=request.chapter_title,
                    input_path=input_path,
                    output_path=output_path,
                    source_language=request.source_language,
                    target_language=request.target_language,
                    translation_style=request.translation_style,
                )
            )
        return command


class GeminiTranslationBackend:
    """Google Gemini translation backend."""

    def __init__(
        self,
        backend_name: str,
        model: str,
        temperature: float,
        api_key_env: str | None,
    ):
        self._name = backend_name
        self._model = model
        self._temperature = temperature
        self._api_key_env = api_key_env or "GEMINI_API_KEY"

    @property
    def name(self) -> str:
        return self._name

    def translate(self, request: TranslationRequest) -> str:
        api_key = os.getenv(self._api_key_env)
        if not api_key:
            raise RuntimeError(f"missing environment variable: {self._api_key_env}")

        client = genai.Client(api_key=api_key)
        prompt = _build_translation_prompt(request)
        response = client.models.generate_content(
            model=self._model,
            contents=[prompt],
            config={"temperature": self._temperature},
        )
        if not response.text:
            raise RuntimeError(f"Gemini backend '{self.name}' returned an empty response")
        return response.text.strip() + "\n"


class OpenAICompatibleTranslationBackend:
    """OpenAI-compatible HTTP backend (works with local vLLM servers)."""

    def __init__(
        self,
        backend_name: str,
        model: str,
        base_url: str,
        temperature: float,
        api_key_env: str | None,
    ):
        self._name = backend_name
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._temperature = temperature
        self._api_key_env = api_key_env or "OPENAI_API_KEY"

    @property
    def name(self) -> str:
        return self._name

    def translate(self, request: TranslationRequest) -> str:
        api_key = os.getenv(self._api_key_env, "")
        payload = {
            "model": self._model,
            "temperature": self._temperature,
            "messages": [
                {"role": "system", "content": "You are a rigorous literary translation assistant."},
                {"role": "user", "content": _build_translation_prompt(request)},
            ],
        }

        response = requests.post(
            f"{self._base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=1800,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"OpenAI-compatible backend '{self.name}' failed: {response.status_code} {response.text[:300]}"
            )

        body = response.json()
        choices = body.get("choices", [])
        if not choices:
            raise RuntimeError(f"OpenAI-compatible backend '{self.name}' returned no choices")
        message = choices[0].get("message", {})
        text = message.get("content", "")
        if not text:
            raise RuntimeError(f"OpenAI-compatible backend '{self.name}' returned empty content")
        return str(text).strip() + "\n"


def build_translation_backends(configs: list[TranslationBackendConfig]) -> list[TranslationBackend]:
    """Instantiate enabled translation backends from config."""
    backends: list[TranslationBackend] = []
    for backend in configs:
        if not backend.enabled:
            continue

        if backend.kind == TranslationBackendKind.shell:
            if backend.shell is None:
                raise ValueError(f"shell config missing for translation backend '{backend.name}'")
            backends.append(ShellTranslationBackend(backend.name, backend.shell))
        elif backend.kind == TranslationBackendKind.gemini:
            if backend.model is None:
                raise ValueError(f"model missing for translation backend '{backend.name}'")
            backends.append(
                GeminiTranslationBackend(
                    backend_name=backend.name,
                    model=backend.model,
                    temperature=backend.temperature,
                    api_key_env=backend.api_key_env,
                )
            )
        elif backend.kind == TranslationBackendKind.openai_compatible:
            if backend.model is None or backend.base_url is None:
                raise ValueError(f"model/base_url missing for translation backend '{backend.name}'")
            backends.append(
                OpenAICompatibleTranslationBackend(
                    backend_name=backend.name,
                    model=backend.model,
                    base_url=backend.base_url,
                    temperature=backend.temperature,
                    api_key_env=backend.api_key_env,
                )
            )
        else:
            raise ValueError(f"unsupported translation backend kind: {backend.kind}")

    if not backends:
        raise ValueError("no enabled translation backends")

    return backends


def _build_translation_prompt(request: TranslationRequest) -> str:
    brief = request.translation_brief or "No additional brief provided."
    return (
        f"Translate the following chapter from {request.source_language} to {request.target_language}.\n"
        f"Style: {request.translation_style}.\n"
        "Preserve structure, headings, footnotes, and paragraph boundaries.\n"
        "Do not summarize. Do not omit lines.\n"
        f"Additional brief: {brief}\n\n"
        f"Chapter ID: {request.chapter_id}\n"
        f"Chapter Title: {request.chapter_title}\n\n"
        "Source chapter:\n"
        f"{request.source_text}"
    )
