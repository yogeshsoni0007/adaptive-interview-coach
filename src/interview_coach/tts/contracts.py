from dataclasses import dataclass
from typing import Protocol


class TTSError(Exception):
    """Safe provider failure; do not include credentials or question text."""


@dataclass(frozen=True)
class AudioResult:
    provider: str
    audio: bytes = b""
    mime_type: str = "audio/mpeg"

    @property
    def is_browser(self) -> bool:
        return self.provider == "browser"


class TTSProvider(Protocol):
    name: str

    def is_configured(self) -> bool: ...

    def synthesize(self, text: str, timeout: float) -> AudioResult: ...
