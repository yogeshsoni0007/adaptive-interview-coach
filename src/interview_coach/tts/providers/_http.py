"""Shared HTTP transport: no automatic retries, redirects, or response-body logging."""

import time

import httpx

from ..config import TTSConfig
from ..contracts import AudioResult, TTSError

MAX_RESPONSE_BYTES = 12 * 1024 * 1024


class HTTPProvider:
    name: str

    def __init__(self, config: TTSConfig):
        self.config = config

    def post(self, url: str, timeout: float, **kwargs) -> bytes:
        started = time.monotonic()
        try:
            with httpx.stream("POST", url, timeout=timeout, follow_redirects=False, **kwargs) as r:
                if r.status_code != 200:
                    raise TTSError(f"{self.name}: HTTP {r.status_code}")
                chunks = []
                size = 0
                for chunk in r.iter_bytes():
                    size += len(chunk)
                    if size > MAX_RESPONSE_BYTES:
                        raise TTSError(f"{self.name}: audio response too large")
                    if time.monotonic() - started > timeout:
                        raise TTSError(f"{self.name}: response timed out")
                    chunks.append(chunk)
                return b"".join(chunks)
        except httpx.HTTPError:
            raise TTSError(f"{self.name}: request failed") from None

    def audio_result(self, audio: bytes) -> AudioResult:
        if audio.startswith(b"RIFF") and audio[8:12] == b"WAVE" and len(audio) > 44:
            return AudioResult(self.name, audio, "audio/wav")
        if len(audio) > 3 and (
            audio.startswith(b"ID3") or (audio[0] == 0xFF and audio[1] & 0xE0 == 0xE0)
        ):
            return AudioResult(self.name, audio)
        raise TTSError(f"{self.name}: invalid or empty audio")
