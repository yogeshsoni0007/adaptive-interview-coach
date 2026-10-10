from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError

from interview_coach.config import Settings
from interview_coach.document import DocumentError, extract_text
from interview_coach.prompt import MAX_TOTAL_QUESTIONS
from interview_coach.provider import OpenAIQuestionProvider, ProviderError
from interview_coach.recording import save_answer_recording
from interview_coach.service import AdaptiveInterviewService, InterviewQuestionService
from interview_coach.speech import render_question_speech
from interview_coach.transcription import TranscriptionError, transcribe_audio

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv()  # Keep support for this project's existing parent-directory .env.
logger = logging.getLogger(__name__)
RECORDINGS_ROOT = PROJECT_ROOT / "recordings"
MAX_FOLLOW_UPS = 2

st.set_page_config(page_title="AI Interview Coach", page_icon="🎙️", layout="wide")
for name, default in {
    "question_set": None,
    "current_question_index": 0,
    "recorded_answers": {},
    "interview_session_id": None,
    "active_question": None,
    "follow_up_count": 0,
    "total_questions_asked": 0,
    "current_turn_question_number": None,
    "interview_complete": False,
    "resume_text": "",
    "job_description": "",
    "experience_level": "senior",
    "pending_answer": None,
    "last_answer": None,
}.items():
    st.session_state.setdefault(name, default)

st.title("AI Interview Coach")
st.caption("Adaptive interview · answer analysis · up to 2 follow-ups per question")
left, right = st.columns(2)
with left:
    st.subheader("Resume")
    resume_file = st.file_uploader("Upload a resume", type=["pdf", "docx"])
    target_level = st.selectbox(
        "Target experience level",
        ["junior", "intermediate", "senior"],
        index=2,
    )
with right:
    st.subheader("Job description")
    jd_mode = st.segmented_control(
        "Input method",
        options=["Paste text", "Upload file"],
        default="Paste text",
    )
    jd_file = None
    jd_text_input = ""
    if jd_mode == "Upload file":
        jd_file = st.file_uploader("Upload a job description", type=["pdf", "docx", "txt"])
    else:
        jd_text_input = st.text_area("Paste the job description", height=220)

if st.button("Generate interview questions", type="primary", width="stretch"):
    if resume_file is None:
        st.error("Upload a resume before generating questions.")
        st.stop()
    try:
        resume_text = extract_text(resume_file.name, resume_file.getvalue())
        job_description = (
            extract_text(jd_file.name, jd_file.getvalue()) if jd_file else jd_text_input.strip()
        )
        if not job_description:
            raise DocumentError("Paste or upload a job description before generating questions.")
        service = InterviewQuestionService(OpenAIQuestionProvider(Settings.from_env()))
        with st.spinner("Analyzing the resume and job description..."):
            question_set = service.generate(resume_text, job_description)
        # Commit the new context only after generation succeeds.
        st.session_state.update(
            {
                "question_set": question_set,
                "resume_text": resume_text,
                "job_description": job_description,
                "experience_level": target_level,
                "interview_session_id": uuid4().hex[:12],
                "current_question_index": 0,
                "recorded_answers": {},
                "active_question": None,
                "follow_up_count": 0,
                "total_questions_asked": 0,
                "current_turn_question_number": None,
                "interview_complete": False,
                "pending_answer": None,
                "last_answer": None,
            }
        )
        st.success(f"{len(question_set.questions)} interview questions generated.")
    except ValidationError:
        st.error("The model returned an invalid question set. Please generate the interview again.")
    except (ProviderError, ValueError) as exc:
        st.error(str(exc))
    except Exception as exc:  # noqa: BLE001 - show a safe error without logging document payloads
        logger.error("Question generation failed (%s)", type(exc).__name__)
        st.error("Question generation failed unexpectedly. Please try again.")

question_set = st.session_state.question_set
if question_set is None:
    st.stop()

st.caption("Changing setup inputs takes effect when you generate a new interview.")
st.subheader("Interview focus")
st.write(question_set.summary)
last_answer = st.session_state.last_answer
if last_answer:
    last_analysis = last_answer["analysis"]
    st.info(
        f"Previous answer: {last_analysis['action'].title()} · {last_analysis['answer_quality']}"
    )
    with st.expander("View transcript and analysis"):
        st.write(last_answer["transcript"])
        st.write(last_analysis["reasoning"])

question_index = st.session_state.current_question_index
follow_up_count = st.session_state.follow_up_count
questions = question_set.questions
if st.session_state.interview_complete or question_index >= len(questions):
    st.success("Interview complete.")
    st.write(f"You recorded {len(st.session_state.recorded_answers)} answers including follow-ups.")
    for turn_id, answer in st.session_state.recorded_answers.items():
        st.markdown(f"**{answer.get('question', 'Saved answer')}**")
        st.audio(answer["audio"], format=answer["mime_type"])
        st.write(answer.get("transcript", ""))
        st.download_button(
            "Download answer",
            data=answer["audio"],
            file_name=Path(answer["audio_path"]).name,
            mime=answer["mime_type"],
            key=f"download_{turn_id}",
        )
    st.stop()

current_item = questions[question_index]
active_question = st.session_state.active_question or current_item.question
if st.session_state.current_turn_question_number is None:
    next_question_number = st.session_state.total_questions_asked + 1
    if next_question_number > MAX_TOTAL_QUESTIONS:
        st.session_state.interview_complete = True
        st.rerun()
    st.session_state.total_questions_asked = next_question_number
    st.session_state.current_turn_question_number = next_question_number

total_question_number = st.session_state.current_turn_question_number
turn_id = f"{st.session_state.interview_session_id}_{total_question_number}"
st.subheader(f"Question {total_question_number} of {MAX_TOTAL_QUESTIONS}")
if follow_up_count:
    st.subheader(f"Follow-up {follow_up_count} of {MAX_FOLLOW_UPS}")
with st.container(border=True):
    st.markdown(f"### {active_question}")
    metadata = st.columns(3)
    metadata[0].metric("Competency", current_item.competency)
    metadata[1].metric("Difficulty", current_item.difficulty.title())
    metadata[2].metric("Source", current_item.source_focus.replace("_", " ").title())
    with st.expander("Question guidance"):
        st.write(current_item.rationale)
        st.write(current_item.expected_evidence)

st.subheader("Listen to the question")
render_question_speech([active_question])
st.subheader("Record your answer")
# Each turn gets a fresh microphone widget, including follow-ups within a competency.
audio_answer = st.audio_input(
    "Click the microphone button and answer the question",
    sample_rate=48000,
    key=f"answer_audio_{turn_id}",
)
pending = st.session_state.pending_answer
if pending and pending["turn_id"] != turn_id:
    pending = None
    st.session_state.pending_answer = None
if audio_answer is not None:
    st.audio(audio_answer)
if audio_answer is None and pending is None:
    st.stop()

if pending and pending.get("error"):
    st.error(pending["error"])
    st.info("Your answer is saved. Click Retry saved answer below to continue this question.")

if not st.button(
    "Retry saved answer" if pending else "Save and analyze answer",
    key=f"submit_{turn_id}",
    type="primary",
    width="stretch",
):
    st.stop()

audio_bytes = audio_answer.getvalue() if audio_answer is not None else pending["audio"]
if pending is None or pending["audio"] != audio_bytes:
    pending = {
        "turn_id": turn_id,
        "audio": audio_bytes,
        "mime_type": getattr(audio_answer, "type", None) or "audio/wav",
        "transcript": None,
        "analysis": None,
    }
    st.session_state.pending_answer = pending
pending.pop("error", None)

recording_args = {
    "root": RECORDINGS_ROOT,
    "session_id": st.session_state.interview_session_id,
    "question_number": question_index + 1,
    "follow_up_number": follow_up_count,
    "question": active_question,
    "audio_bytes": audio_bytes,
}
try:
    audio_path = save_answer_recording(
        **recording_args,
        transcript=pending["transcript"],
        analysis=pending["analysis"],
        status="analyzing" if pending["transcript"] else "transcribing",
    )
except (OSError, ValueError) as exc:
    logger.error("Recording save failed (%s)", type(exc).__name__)
    st.error("Could not save your answer. The question has not changed. Please retry.")
    st.stop()

if not pending["transcript"]:
    try:
        with st.spinner("Transcribing your saved answer..."):
            transcript = transcribe_audio(audio_path).strip()
        if not transcript:
            raise TranscriptionError("No speech was detected. Please record your answer again.")
        pending["transcript"] = transcript
    except TranscriptionError as exc:
        try:
            save_answer_recording(
                **recording_args,
                transcription_error=str(exc),
                status="transcription_failed",
            )
        except (OSError, ValueError):
            st.warning("The audio is saved, but its error details could not be saved.")
        logger.warning("Transcription failed for turn %s", turn_id)
        st.error(str(exc))
        st.info("Your recording is saved. Retry or record again; this question stays active.")
        st.stop()

if pending["analysis"] is None:
    try:
        # Save the transcript before the model call, so an interruption cannot lose it.
        save_answer_recording(
            **recording_args, transcript=pending["transcript"], status="analyzing"
        )
        history = "\n\n".join(
            f"Question: {item['question']}\nAnswer: {item['transcript']}"
            for item in st.session_state.recorded_answers.values()
            if item.get("question_number") == question_index + 1
        )
        with st.spinner("Analyzing your answer and choosing the next question..."):
            service = AdaptiveInterviewService(OpenAIQuestionProvider(Settings.from_env()))
            analysis = service.analyze_answer(
                question=active_question,
                answer=pending["transcript"],
                resume_text=st.session_state.resume_text,
                job_description=st.session_state.job_description,
                competency=current_item.competency,
                experience_level=st.session_state.experience_level,
                follow_up_count=follow_up_count,
                max_follow_ups=MAX_FOLLOW_UPS,
                total_questions_asked=total_question_number,
                previous_context=history,
            )
        pending["analysis"] = analysis.model_dump()
    except Exception as exc:  # noqa: BLE001 - preserve the answer and allow retry on any failure
        # Provider errors are sanitized; never display raw SDK/validation payloads.
        error = (
            str(exc)
            if isinstance(exc, ProviderError)
            else (f"Answer analysis could not complete ({type(exc).__name__}). Please retry.")
        )
        try:
            save_answer_recording(
                **recording_args,
                transcript=pending["transcript"],
                analysis_error=error,
                status="analysis_failed",
            )
        except (OSError, ValueError):
            st.warning("The audio is saved, but analysis error details could not be saved.")
        logger.warning("Analysis failed for turn %s (%s)", turn_id, type(exc).__name__)
        pending["error"] = error
        st.rerun()

try:
    save_answer_recording(
        **recording_args,
        transcript=pending["transcript"],
        analysis=pending["analysis"],
        status="complete",
    )
except (OSError, ValueError):
    st.error("Could not save the analysis. Retry saved answer; no new model call is needed.")
    st.stop()

saved = {
    **pending,
    "question": active_question,
    "question_number": question_index + 1,
    "follow_up_number": follow_up_count,
    "audio_path": str(audio_path),
}
st.session_state.recorded_answers[turn_id] = saved
st.session_state.last_answer = saved
analysis = pending["analysis"]
logger.info("Interview turn %s completed: action=%s", turn_id, analysis["action"])
if total_question_number >= MAX_TOTAL_QUESTIONS:
    st.session_state.interview_complete = True
    st.session_state.active_question = None
    st.session_state.follow_up_count = 0
elif analysis["action"] == "advance":
    st.session_state.current_question_index += 1
    st.session_state.active_question = None
    st.session_state.follow_up_count = 0
else:
    st.session_state.active_question = analysis["follow_up_question"]
    st.session_state.follow_up_count += 1
st.session_state.current_turn_question_number = None
st.session_state.pending_answer = None
st.rerun()
