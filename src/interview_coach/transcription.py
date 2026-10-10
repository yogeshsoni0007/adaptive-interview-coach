from __future__ import annotations

from pathlib import Path


class TranscriptionError(RuntimeError):
    """Raised when local audio transcription cannot be completed."""


def transcribe_audio(audio_path: Path, model: str = "mlx-community/whisper-tiny") -> str:
    """Transcribe a saved audio file with the local MLX Whisper model."""

    if not audio_path.exists():
        raise TranscriptionError(f"Audio file not found: {audio_path}")

    try:
        import mlx_whisper
    except ImportError as exc:
        raise TranscriptionError(
            "Local transcription is unavailable. Install mlx-whisper to enable it."
        ) from exc

    try:
        result = mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=model,
        )
    except Exception as exc:
        raise TranscriptionError("The answer was saved, but transcription failed.") from exc

    transcript = result.get("text", "").strip()
    if not transcript:
        raise TranscriptionError("The answer was saved, but no speech was detected.")

    return transcript
