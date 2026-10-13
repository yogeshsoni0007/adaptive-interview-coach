"""Bounded memory cache owned by one interview's TTSService, never shared globally."""

from collections import OrderedDict
from hashlib import sha256
from time import monotonic

from .contracts import AudioResult


class AudioCache:
    def __init__(self, max_bytes: int, max_entries: int = 64):
        self.max_bytes = max_bytes
        self.max_entries = max_entries
        self.entries: OrderedDict[str, tuple[AudioResult, float]] = OrderedDict()
        self.size = 0

    @staticmethod
    def key(text: str) -> str:
        # The owning service has immutable provider/voice/speed/language settings.
        return sha256(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> AudioResult | None:
        key = self.key(text)
        entry = self.entries.get(key)
        if entry is None:
            return None
        result, expires = entry
        if monotonic() >= expires:
            self.size -= len(self.entries.pop(key)[0].audio)
            return None
        self.entries.move_to_end(key)
        return result

    def put(self, text: str, result: AudioResult, ttl: float = 3600) -> None:
        if len(result.audio) > self.max_bytes:
            return
        key = self.key(text)
        old = self.entries.pop(key, None)
        if old:
            self.size -= len(old[0].audio)
        self.entries[key] = (result, monotonic() + ttl)
        self.size += len(result.audio)
        while self.size > self.max_bytes or len(self.entries) > self.max_entries:
            self.size -= len(self.entries.popitem(last=False)[1][0].audio)
