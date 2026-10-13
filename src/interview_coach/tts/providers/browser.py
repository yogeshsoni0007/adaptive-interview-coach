from ..config import TTSConfig
from ..contracts import AudioResult


class BrowserProvider:
    name = "browser"

    def __init__(self, config: TTSConfig):
        self.config = config

    def is_configured(self) -> bool:
        return True

    def synthesize(self, text: str, timeout: float) -> AudioResult:
        # Browser speech runs in playback.js; it cannot return server-side bytes.
        return AudioResult(self.name)
