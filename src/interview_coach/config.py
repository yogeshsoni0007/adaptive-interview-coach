from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_OLLAMA_MODEL = "qwen3:4b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1/"
DEFAULT_GEMINI_BASE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/openai/"
)


class SettingsError(ValueError):
    """Raised when application configuration is missing or invalid."""


@dataclass(frozen=True)
class ModelCandidate:
    name: str
    model: str
    api_key: str
    base_url: str


@dataclass(frozen=True)
class Settings:
    candidates: tuple[ModelCandidate, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        candidates = [
            ModelCandidate(
                name="Ollama Qwen",
                model=os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL).strip(),
                api_key=os.getenv("OLLAMA_API_KEY", "ollama").strip() or "ollama",
                base_url=os.getenv(
                    "OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL
                ).strip(),
            )
        ]

        gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        gemini_model = os.getenv("GEMINI_MODEL", "").strip()

        if gemini_api_key or gemini_model:
            if not gemini_api_key or not gemini_model:
                raise SettingsError(
                    "Set both GEMINI_API_KEY and GEMINI_MODEL "
                    "to enable Gemini fallback."
                )

            candidates.append(
                ModelCandidate(
                    name="Google Gemini",
                    model=gemini_model,
                    api_key=gemini_api_key,
                    base_url=os.getenv(
                        "GEMINI_BASE_URL", DEFAULT_GEMINI_BASE_URL
                    ).strip(),
                )
            )
        # Temporary debug only — exposes API keys, remove after testing.
        # print(candidates)
        return cls(candidates=tuple(candidates))
