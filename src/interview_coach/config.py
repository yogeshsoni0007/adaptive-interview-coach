from __future__ import annotations

import os
from dataclasses import dataclass


# Default model settings
DEFAULT_OLLAMA_MODEL = "qwen3:4b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1/"

DEFAULT_GEMINI_BASE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/openai/"
)

DEFAULT_ANTHROPIC_MODEL = "claude-haiku-5-5"
DEFAULT_ANTHROPIC_BASE_URL = "https://api.anthropic.com"


class SettingsError(ValueError):
    """Raised when the model configuration is invalid."""


@dataclass(frozen=True)
class ModelCandidate:
    name: str
    model: str
    api_key: str
    base_url: str

    # Tells provider.py which API format to use.
    protocol: str = "openai_compatible"

    # Used in MODEL_PRIORITY.
    key: str = ""


@dataclass(frozen=True)
class Settings:
    candidates: tuple[ModelCandidate, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        """
        Read model settings from environment variables.
        """

        # Ollama is always available as the first default option.
        candidates = [
            ModelCandidate(
                name="Ollama Qwen",
                model=(
                    os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL).strip()
                    or DEFAULT_OLLAMA_MODEL
                ),
                api_key=os.getenv("OLLAMA_API_KEY", "ollama").strip()
                or "ollama",
                base_url=(
                    os.getenv(
                        "OLLAMA_BASE_URL",
                        DEFAULT_OLLAMA_BASE_URL,
                    ).strip()
                    or DEFAULT_OLLAMA_BASE_URL
                ),
                protocol="openai_compatible",
                key="ollama",
            )
        ]

        # Gemini is optional.
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        gemini_model = os.getenv("GEMINI_MODEL", "").strip()

        if gemini_key or gemini_model:
            if not gemini_key or not gemini_model:
                raise SettingsError(
                    "Set both GEMINI_API_KEY and GEMINI_MODEL "
                    "to enable Gemini."
                )

            candidates.append(
                ModelCandidate(
                    name="Google Gemini",
                    model=gemini_model,
                    api_key=gemini_key,
                    base_url=(
                        os.getenv(
                            "GEMINI_BASE_URL",
                            DEFAULT_GEMINI_BASE_URL,
                        ).strip()
                        or DEFAULT_GEMINI_BASE_URL
                    ),
                    protocol="openai_compatible",
                    key="gemini",
                )
            )

        # Anthropic is optional.
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        anthropic_model_from_env = os.getenv("ANTHROPIC_MODEL", "").strip()

        if anthropic_key or anthropic_model_from_env:
            if not anthropic_key:
                raise SettingsError(
                    "Set ANTHROPIC_API_KEY to enable Anthropic."
                )

            candidates.append(
                ModelCandidate(
                    name="Claude Haiku 5.5",
                    model=(
                        anthropic_model_from_env
                        or DEFAULT_ANTHROPIC_MODEL
                    ),
                    api_key=anthropic_key,
                    base_url=(
                        os.getenv(
                            "ANTHROPIC_BASE_URL",
                            DEFAULT_ANTHROPIC_BASE_URL,
                        ).strip()
                        or DEFAULT_ANTHROPIC_BASE_URL
                    ),
                    protocol="anthropic",
                    key="anthropic",
                )
            )

        # Reorder models only when MODEL_PRIORITY is provided.
        priority_text = os.getenv("MODEL_PRIORITY", "").strip()

        if priority_text:
            priority_keys = [
                item.strip().lower()
                for item in priority_text.split(",")
                if item.strip()
            ]

            if len(priority_keys) != len(set(priority_keys)):
                raise SettingsError(
                    "MODEL_PRIORITY contains a duplicate model."
                )

            candidates_by_key = {
                candidate.key: candidate
                for candidate in candidates
            }

            ordered_candidates = []

            for key in priority_keys:
                if key not in candidates_by_key:
                    raise SettingsError(
                        f"MODEL_PRIORITY refers to '{key}', "
                        "but that model is not configured."
                    )

                ordered_candidates.append(candidates_by_key[key])

            # Add configured models that were not explicitly listed.
            for candidate in candidates:
                if candidate.key not in priority_keys:
                    ordered_candidates.append(candidate)

            candidates = ordered_candidates

        return cls(candidates=tuple(candidates))

## Confirm that the settings are valid and that at least one model is configured.
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    try:
        settings = Settings.from_env()

        print("Effective model priority:")

        for position, candidate in enumerate(
            settings.candidates,
            start=1,
        ):
            print(
                f"{position}. "
                f"{candidate.key} - "
                f"{candidate.name} - "
                f"{candidate.model}"
            )

    except SettingsError as error:
        print(f"Configuration error: {error}")