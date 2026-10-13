"""Connect to a separately installed Kokoro-FastAPI server on this machine."""

from urllib.parse import urlsplit

from ._http import HTTPProvider


class LocalProvider(HTTPProvider):
    name = "local"

    def is_configured(self) -> bool:
        try:
            url = urlsplit(self.config.local_base_url)
            return (
                url.scheme in {"http", "https"}
                and url.hostname in {"localhost", "127.0.0.1", "::1"}
                and not url.username
                and not url.password
                and not url.query
                and not url.fragment
            )
        except ValueError:
            return False

    def synthesize(self, text: str, timeout: float):
        c = self.config
        audio = self.post(
            c.local_base_url.rstrip("/") + "/audio/speech",
            timeout,
            json={
                "model": c.local_model,
                "input": text,
                "voice": c.local_voice,
                "response_format": "mp3",
                "speed": c.speed,
            },
        )
        return self.audio_result(audio)
