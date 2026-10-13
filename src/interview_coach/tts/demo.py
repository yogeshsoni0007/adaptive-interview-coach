"""Standalone playback check, separate from resume upload and question generation."""

import streamlit as st
from dotenv import find_dotenv, load_dotenv

from interview_coach.speech import render_question_speech

load_dotenv(find_dotenv(usecwd=True))
st.title("Interview question audio test")
st.caption("Preparing audio uses the configured provider and may consume its paid quota.")
text = st.text_area("Question", "Tell me about a process improvement you led and its outcome.")
if st.button("Prepare audio") and text.strip():
    st.session_state["tts_demo_text"] = text
if st.session_state.get("tts_demo_text"):
    render_question_speech([st.session_state.tts_demo_text])
