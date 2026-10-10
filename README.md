# AI Interview Coach

Local interview coach with answer analysis and adaptive follow-up questions.

## What this version does

- Accepts a resume as PDF or DOCX.
- Accepts a job description as pasted text or a PDF, DOCX, or TXT upload.
- Extracts text locally.
- Generates a question plan using local Ollama first, with optional OpenAI-compatible fallback.
- Records answers, saves audio locally, and transcribes with MLX Whisper on supported Macs.
- Analyzes each transcript and asks a probe, clarification, or challenge, or advances.
- Enforces a maximum of two follow-ups per planned question in code.
- Shows the last analysis and transcript, and labels follow-ups explicitly.
- Preserves separate audio and metadata for each original answer and follow-up.
- Pauses on transcription, analysis, or saving failures. Retry reuses completed work.

## Local setup

Requires Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

By default, Ollama must be running locally with `qwen3:4b` installed. Optional
configuration goes in `.env` beside `app.py` (an existing parent-directory `.env` also works):
`OLLAMA_MODEL`, `OLLAMA_BASE_URL`,
and, for Gemini fallback, both `GEMINI_MODEL` and `GEMINI_API_KEY`.
Then run from this project directory:

```bash
streamlit run app.py
```

Open the local URL printed by Streamlit.

After activating the virtual environment, run:

```bash
python -m streamlit run app.py
```

## Check the adaptive flow

1. Refresh the app. Confirm the caption says **Adaptive interview** and generate a new interview.
2. Record a deliberately vague answer, such as “I improved the process. Things got better.”
3. Click **Save and analyze answer**. Wait through transcription and analysis.
4. Look for **Follow-up 1 of 2**, a targeted question, and a fresh microphone control.
5. Use the speech controls to hear the new question, then record a new answer.

A sufficiently detailed answer can advance directly; every answer does not need a follow-up.
Errors keep the current question active and offer **Retry saved answer**. Stop/start Streamlit
if an old process is still showing the old interface.

If question generation or answer analysis fails schema validation, the provider makes at most one correction attempt
on that same model. It retains strict validation: invalid actions and missing follow-up questions
cannot silently advance the interview. If correction fails, the UI shows the failing field/type
without exposing raw model content, and the retry button reuses the saved recording/transcript.
Failed question generation preserves the existing interview. An empty question list is rejected
both in the schema sent to the model and when validating its response.
Valid responses still require only one model call. Use Streamlit's **Rerun** to load a code update
while preserving the current browser session and its pending answer.

For Qwen3 on local Ollama port 11434, requests use the native structured-output endpoint.
The analysis output constraints require a question for probe/clarify/challenge and JSON null
for advance. Thinking is disabled for both operations. Generation is capped at 3,000 output
tokens and 180 seconds per request; analysis at 800 tokens and 120 seconds.
The local context is selected as 8,192 or 16,384 tokens using a conservative input-size estimate
with output space reserved. Oversized inputs get a clear error instead of intentionally dropping
document text. Other endpoints retain the OpenAI-compatible path.

Audio files use `question_01.wav`, `question_01_followup_01.wav`, etc. Metadata includes the
actual question asked, transcript, analysis, processing status, and failure details.

## Tests and linting

```bash
python -m pytest
python -m ruff check app.py src/interview_coach/provider.py src/interview_coach/schemas.py src/interview_coach/prompt.py src/interview_coach/service.py src/interview_coach/recording.py tests/test_adaptive_flow.py tests/test_provider.py
```

The default suite uses mocks and costs no model tokens. Streamlit AppTest runs the real
application submission/rerun flow, while mocked HTTP responses exercise SDK parsing and failover.

An opt-in integration test uses a WAV containing a vague answer, cached local Whisper,
and local Qwen. It verifies that a real transcription produces a visible follow-up:

```bash
INTERVIEW_LIVE_WAV=/absolute/path/to/vague-answer.wav HF_HUB_OFFLINE=1 python -m pytest tests/test_adaptive_flow.py::test_live_local_audio_to_visible_followup -q -s
```

This test uses synthetic setup documents/questions and no paid provider. It injects recorded
audio at the microphone widget boundary; physical microphone permissions and browser speech
playback still need a manual check. Other providers keep their usual thinking settings.

The full local integration test also generates ten real questions from long synthetic documents
and runs the entire interview through follow-ups and completion:

```bash
INTERVIEW_LIVE_FULL_WAV=/absolute/path/to/vague-answer.wav HF_HUB_OFFLINE=1 python -m pytest tests/test_adaptive_flow.py::test_live_generation_audio_followups_and_completion -q -s
```

It uses real local Qwen and Whisper with temporary recordings, not your saved interview.
Expect one generation plus up to thirty analyses (one original answer and two follow-ups per
question). This is an opt-in diagnostic, not a command to run routinely. It does not test the
physical microphone or audible browser playback.

To replay an already saved answer without retranscribing or altering its original files:

```bash
INTERVIEW_SAVED_METADATA=/absolute/path/to/metadata.json python -m pytest tests/test_adaptive_flow.py::test_live_saved_answer_to_visible_followup -q -s
```

This opt-in check uses the latest answer in that file, local Qwen, temporary output files,
and synthetic resume/JD context. Use a session whose last answer should warrant a follow-up.

## Security

Resume and job-description text are held in memory. The configured provider receives this text
and transcripts for analysis. Audio, transcripts, and analysis are saved locally in `recordings/`.
Do not commit `.env`, recordings, or candidate data. Automatic retention is not implemented yet.

## Project structure

```text
app.py                              Streamlit user interface
src/interview_coach/config.py       Environment configuration
src/interview_coach/document.py     PDF, DOCX, and TXT extraction
src/interview_coach/provider.py     LLM provider boundary
src/interview_coach/schemas.py      Validated output contract
src/interview_coach/service.py      Application workflow
src/interview_coach/recording.py    Per-turn audio and metadata storage
tests/                             Unit/UI tests and opt-in local integration check
```
