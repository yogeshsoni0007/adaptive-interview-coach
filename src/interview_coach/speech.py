"""Compatibility entry point used by the existing interview application."""

from .tts.playback import render_question_speech

__all__ = ["render_question_speech"]
