import logging
from time import monotonic

from .cache import AudioCache
from .config import TTSConfig
from .contracts import AudioResult, TTSError, TTSProvider
from .providers import build_providers

logger = logging.getLogger(__name__)


class TTSService:
    def __init__(self, config: TTSConfig, providers: dict[str, TTSProvider] | None = None):
        self.config = config
        self.providers = build_providers(config) if providers is None else providers
        self.cache = AudioCache(config.cache_max_bytes)
        self.cooldowns: dict[str, float] = {}

    def synthesize(self, text: str) -> AudioResult:
        if not text.strip():
            return AudioResult("browser")
        cached = self.cache.get(text)
        if cached is not None:
            return cached
        if len(text.encode("utf-8")) > self.config.max_input_bytes:
            return AudioResult("browser")
        deadline = monotonic() + self.config.fallback_budget_seconds
        for name in self.config.priority:
            if name == "browser":
                break
            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            if self.cooldowns.get(name, 0) > monotonic():
                continue
            provider = self.providers.get(name)
            try:
                if provider is None or not provider.is_configured():
                    continue
                result = provider.synthesize(text, min(self.config.timeout_seconds, remaining))
                if not result.audio or result.is_browser:
                    raise TTSError("Provider did not return audio")
                self.cache.put(text, result)
                return result
            except Exception as exc:  # noqa: BLE001 - provider failures must not break interviews
                # A provider bug/failure must never break question or answer handling.
                logger.warning("TTS provider %s unavailable (%s)", name, type(exc).__name__)
                self.cooldowns[name] = monotonic() + self.config.cooldown_seconds
        result = AudioResult("browser")
        self.cache.put(text, result, ttl=self.config.cooldown_seconds)
        return result
