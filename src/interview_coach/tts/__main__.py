"""Read-only configuration check: python -m interview_coach.tts."""

from dotenv import find_dotenv, load_dotenv

from .config import TTSConfig
from .providers import build_providers


def main() -> None:
    load_dotenv(find_dotenv(usecwd=True))
    try:
        config = TTSConfig.from_env()
    except (ValueError, TypeError):
        raise SystemExit(
            "Invalid TTS configuration. Check tts/config.py and TTS_ variables."
        ) from None
    providers = build_providers(config)
    print("Priority: " + " -> ".join(config.priority))
    for name in config.priority:
        status = "configured" if providers[name].is_configured() else "not configured; skipped"
        if name == "browser":
            status = "final fallback; requires browser speech support"
        print(f"{name}: {status}")
    print("Configuration only: no network requests, audio generation, or charges.")


if __name__ == "__main__":
    main()
