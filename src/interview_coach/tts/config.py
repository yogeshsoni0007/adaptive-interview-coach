"""Edit DEFAULT_PRIORITY here, or override settings through environment variables."""

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass, field

DEFAULT_PRIORITY = ("elevenlabs", "google", "azure", "local", "browser")
PROVIDERS = frozenset(DEFAULT_PRIORITY)


@dataclass(frozen=True)
class TTSConfig:
    priority: tuple[str, ...] = DEFAULT_PRIORITY
    language: str = "en-US"
    speed: float = 0.92
    timeout_seconds: float = 4.0
    fallback_budget_seconds: float = 8.0
    cooldown_seconds: float = 60.0
    cache_max_bytes: int = 20 * 1024 * 1024
    max_input_bytes: int = 4500
    elevenlabs_api_key: str = field(default="", repr=False)
    elevenlabs_voice: str = "JBFqnCBsd6RMkjVDRZzb"
    elevenlabs_model: str = "eleven_flash_v2_5"
    google_api_key: str = field(default="", repr=False)
    google_access_token: str = field(default="", repr=False)
    google_project: str = ""
    google_voice: str = "en-US-Neural2-F"
    azure_api_key: str = field(default="", repr=False)
    azure_region: str = ""
    azure_voice: str = "en-US-JennyNeural"
    local_base_url: str = ""
    local_voice: str = "af_bella"
    local_model: str = "kokoro"

    def __post_init__(self):
        unknown = set(self.priority) - PROVIDERS
        if unknown:
            raise ValueError("TTS_PRIORITY contains an unknown provider.")
        # Browser speech is mandatory and always last, even if omitted or moved.
        order = tuple(dict.fromkeys(p for p in self.priority if p != "browser"))
        object.__setattr__(self, "priority", order + ("browser",))
        if not math.isfinite(self.speed) or not 0.7 <= self.speed <= 1.2:
            raise ValueError("TTS_SPEED must be between 0.7 and 1.2.")
        for value in (self.timeout_seconds, self.fallback_budget_seconds, self.cooldown_seconds):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("TTS timeouts and cooldown must be positive finite numbers.")
        if self.cache_max_bytes <= 0 or self.max_input_bytes <= 0:
            raise ValueError("TTS cache and input limits must be positive.")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "TTSConfig":
        env = os.environ if env is None else env
        values = {}
        for name, definition in cls.__dataclass_fields__.items():
            if name == "priority":
                continue
            raw = env.get("TTS_" + name.upper(), "").strip()
            if raw:
                values[name] = type(definition.default)(raw)
        order = env.get("TTS_PRIORITY", ",".join(DEFAULT_PRIORITY))
        values["priority"] = tuple(p.strip().lower() for p in order.split(",") if p.strip())
        return cls(**values)
