import base64
import logging
from pathlib import Path

import streamlit as st

from .config import TTSConfig
from .service import TTSService

logger = logging.getLogger(__name__)
_ROOT = Path(__file__).parent
_HTML = (_ROOT / "playback.html").read_text(encoding="utf-8")
_JS = (_ROOT / "playback.js").read_text(encoding="utf-8")


def _SPEECH(**kwargs):
    # Register in the active Streamlit runtime, including after an imported module is reused.
    component = st.components.v2.component("interview_question_speech", html=_HTML, js=_JS)
    return component(**kwargs)


def render_question_speech(questions: list[str]) -> None:
    """Keep the existing API and controls; prepare only the supplied active questions."""
    if not questions:
        return
    try:
        config = TTSConfig.from_env()
    except (ValueError, TypeError):
        logger.warning("Invalid TTS configuration; using browser speech")
        config = TTSConfig(priority=("browser",))
    session_id = st.session_state.get("interview_session_id")
    state = st.session_state.get("_tts_state")
    if state is None or state[0] != session_id or state[1] != config:
        state = (session_id, config, TTSService(config))
        st.session_state["_tts_state"] = state
    service = state[2]
    audio_urls = []
    for question in questions:
        result = service.synthesize(question)
        audio_urls.append(
            None
            if result.is_browser
            else f"data:{result.mime_type};base64,{base64.b64encode(result.audio).decode('ascii')}"
        )
    _SPEECH(
        data={
            "questions": questions,
            "audio": audio_urls,
            "language": config.language,
            "speed": config.speed,
        },
        key="interview_speech_player",
        height="content",
    )
