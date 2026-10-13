from urllib.parse import quote

from ._http import HTTPProvider


class ElevenLabsProvider(HTTPProvider):
    name = "elevenlabs"

    def is_configured(self) -> bool:
        return bool(self.config.elevenlabs_api_key and self.config.elevenlabs_voice)

    def synthesize(self, text: str, timeout: float):
        c = self.config
        audio = self.post(
            "https://api.elevenlabs.io/v1/text-to-speech/"
            + quote(c.elevenlabs_voice, safe="")
            + "?output_format=mp3_44100_128",
            timeout,
            headers={"xi-api-key": c.elevenlabs_api_key, "Accept": "audio/mpeg"},
            json={
                "text": text,
                "model_id": c.elevenlabs_model,
                "language_code": c.language.split("-")[0],
                "voice_settings": {"speed": c.speed},
            },
        )
        return self.audio_result(audio)
