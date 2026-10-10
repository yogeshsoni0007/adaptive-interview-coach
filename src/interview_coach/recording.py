from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


def save_answer_recording(
    *,
    root: Path,
    session_id: str,
    question_number: int,
    follow_up_number: int,
    question: str,
    audio_bytes: bytes,
    transcript: str | None = None,
    transcription_error: str | None = None,
    analysis: dict | None = None,
    analysis_error: str | None = None,
    status: str = "saved",
) -> Path:
    """Keep every interview turn; retries update only that same turn."""
    interview_dir = root / f"interview_{session_id}"
    interview_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_followup_{follow_up_number:02d}" if follow_up_number else ""
    audio_path = interview_dir / f"question_{question_number:02d}{suffix}.wav"
    audio_path.write_bytes(audio_bytes)

    metadata_path = interview_dir / "metadata.json"
    metadata = (
        json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata_path.exists()
        else {"session_id": session_id, "answers": []}
    )
    metadata["answers"] = [
        item
        for item in metadata["answers"]
        if (item["question_number"], item.get("follow_up_number", 0))
        != (question_number, follow_up_number)
    ]
    metadata["answers"].append(
        {
            "question_number": question_number,
            "follow_up_number": follow_up_number,
            "question": question,
            "audio_file": audio_path.name,
            "transcript": transcript,
            "transcription_error": transcription_error,
            "analysis": analysis,
            "analysis_error": analysis_error,
            "status": status,
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    metadata["answers"].sort(
        key=lambda item: (item["question_number"], item.get("follow_up_number", 0))
    )
    # Replace metadata only after a full JSON write succeeds.
    temporary_path = metadata_path.with_suffix(".tmp")
    temporary_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary_path.replace(metadata_path)
    return audio_path
