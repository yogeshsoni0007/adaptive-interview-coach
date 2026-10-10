from pathlib import Path
from time import perf_counter

import mlx_whisper

AUDIO_FILE = Path("/Users/yogeshsoni/Projects/AI interview /AI_Interview_v1/recordings/interview_7df29840e87e/question_01.wav")

if not AUDIO_FILE.exists():
    raise FileNotFoundError(f"Audio file not found: {AUDIO_FILE}")

start = perf_counter()

result = mlx_whisper.transcribe(
    str(AUDIO_FILE),
    path_or_hf_repo="mlx-community/whisper-tiny",
)

elapsed = perf_counter() - start

print("Transcript:")
print(result["text"].strip())
print(f"\nProcessing time: {elapsed:.2f} seconds")
