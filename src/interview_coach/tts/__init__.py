"""Configurable question audio, independent of the interview workflow."""

from .config import TTSConfig
from .service import TTSService

__all__ = ["TTSConfig", "TTSService"]
