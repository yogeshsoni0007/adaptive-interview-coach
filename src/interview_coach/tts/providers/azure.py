import re
from xml.etree.ElementTree import Element, SubElement, tostring

from ._http import HTTPProvider


class AzureProvider(HTTPProvider):
    name = "azure"

    def is_configured(self) -> bool:
        return bool(
            self.config.azure_api_key and re.fullmatch(r"[a-z0-9-]+", self.config.azure_region)
        )

    def synthesize(self, text: str, timeout: float):
        c = self.config
        root = Element(
            "speak",
            {
                "version": "1.0",
                "xmlns": "http://www.w3.org/2001/10/synthesis",
                "xml:lang": c.language,
            },
        )
        voice = SubElement(root, "voice", {"name": c.azure_voice})
        SubElement(voice, "prosody", {"rate": f"{(c.speed - 1) * 100:+.0f}%"}).text = text
        audio = self.post(
            f"https://{c.azure_region}.tts.speech.microsoft.com/cognitiveservices/v1",
            timeout,
            headers={
                "Ocp-Apim-Subscription-Key": c.azure_api_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
                "User-Agent": "AI-Interview-Coach",
            },
            content=tostring(root, encoding="utf-8"),
        )
        return self.audio_result(audio)
