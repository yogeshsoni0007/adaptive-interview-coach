from ..config import TTSConfig
from ..contracts import TTSProvider
from .azure import AzureProvider
from .browser import BrowserProvider
from .elevenlabs import ElevenLabsProvider
from .google import GoogleProvider
from .local import LocalProvider


def build_providers(config: TTSConfig) -> dict[str, TTSProvider]:
    classes = (ElevenLabsProvider, GoogleProvider, AzureProvider, LocalProvider, BrowserProvider)
    return {cls.name: cls(config) for cls in classes}
