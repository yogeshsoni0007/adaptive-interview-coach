import base64
import binascii
import json

from ..contracts import TTSError
from ._http import HTTPProvider


class GoogleProvider(HTTPProvider):
    name = "google"

    def is_configured(self) -> bool:
        return bool(self.config.google_api_key or self.config.google_access_token)

    def synthesize(self, text: str, timeout: float):
        c = self.config
        headers = {}
        if c.google_access_token:
            headers["Authorization"] = "Bearer " + c.google_access_token
        else:
            headers["x-goog-api-key"] = c.google_api_key
        if c.google_project:
            headers["x-goog-user-project"] = c.google_project
        raw = self.post(
            "https://texttospeech.googleapis.com/v1/text:synthesize",
            timeout,
            headers=headers,
            json={
                "input": {"text": text},
                "voice": {"languageCode": c.language, "name": c.google_voice},
                "audioConfig": {"audioEncoding": "MP3", "speakingRate": c.speed},
            },
        )
        try:
            audio = base64.b64decode(json.loads(raw)["audioContent"], validate=True)
        except (ValueError, KeyError, TypeError, binascii.Error):
            raise TTSError("google: invalid audio response") from None
        return self.audio_result(audio)
