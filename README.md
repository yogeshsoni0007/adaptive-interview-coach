# AI Interview Coach

AI-powered interview coach built with Python and Streamlit.

The application accepts a candidate's resume and job description, creates an adaptive interview plan, records answers, transcribes responses, analyzes performance, and generates targeted follow-up questions.

The application runs locally, while model requests can use local Ollama or cloud providers such as Gemini and Anthropic.

## Current capabilities

- Resume upload support:
  - PDF
  - DOCX
- Job description input support:
  - Pasted text
  - PDF
  - DOCX
  - TXT
- Local document text extraction.
- Adaptive interview question generation.
- Answer recording and local audio storage.
- Speech-to-text transcription with MLX Whisper on supported Macs.
- Answer analysis after every response.
- Adaptive probe, clarification, and challenge questions.
- Maximum of two follow-up questions per planned question.
- Separate storage for original answers and follow-up answers.
- Transcript and analysis metadata storage.
- Retry support for failed transcription or analysis.
- Schema validation for model responses.
- Model fallback when a provider fails.
- Configurable model priority.
- Support for three model providers:
  - Ollama
  - Google Gemini
  - Anthropic Claude
- Provider self-test command.
- Automated unit and integration tests.

## Supported model providers

### Ollama

- Runs locally.
- Requires Ollama to be installed and running.
- Requests remain on the local machine.
- Uses Ollama's native structured-output API.

Example model:

```text
qwen3:4b
```

### Google Gemini

- Runs through Google's cloud API.
- Requires a Gemini API key.
- Uses an OpenAI-compatible API format.

### Anthropic Claude

- Runs through Anthropic's cloud API.
- Requires an Anthropic API key.
- Uses Anthropic's native Messages API.

Anthropic uses a separate API path because its endpoint is not OpenAI-compatible.

## Model priority and fallback

Model priority is controlled through the `MODEL_PRIORITY` environment variable.

Example:

```text
MODEL_PRIORITY=anthropic,gemini,ollama
```

The application tries providers in this order:

1. Anthropic
2. Gemini
3. Ollama

If the first provider fails, the application tries the next configured provider.

Another example:

```text
MODEL_PRIORITY=ollama,gemini,anthropic
```

This makes local Ollama the preferred provider.

Only include providers that are configured and available.

The application does not automatically detect every model installed on the computer. A provider must be configured before it can be used.

## Requirements

- Python 3.11 or newer.
- macOS is recommended for MLX Whisper transcription.
- Ollama is required only when Ollama is included in the provider priority.
- Gemini API access is required when Gemini is included in the provider priority.
- Anthropic API access is required when Anthropic is included in the provider priority.

## Project setup

Open a terminal in the project directory.

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install the project and development dependencies:

```bash
python -m pip install -e ".[dev]"
```

The editable installation allows Python to use the local project source code.

## Environment configuration

The project uses a `.env` file for local configuration.

If `.env` does not already exist, create it from the example file:

```bash
cp -n .env.example .env
```

The `-n` option prevents overwriting an existing `.env` file.

Open `.env` and add the settings required for the providers you want to use.

Example:

```text
# Ollama
OLLAMA_MODEL=qwen3:4b
OLLAMA_BASE_URL=http://localhost:11434/v1/
OLLAMA_API_KEY=ollama

# Gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.5-flash
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/

# Anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key
ANTHROPIC_MODEL=claude-haiku-5-5
ANTHROPIC_BASE_URL=https://api.anthropic.com

# Provider priority
MODEL_PRIORITY=anthropic,gemini,ollama
```

Replace the placeholder API keys in `.env` with real values.

Never add real API keys to `.env.example`.

## Ollama setup

If Ollama is part of `MODEL_PRIORITY`, make sure Ollama is running locally.

Example commands:

```bash
ollama serve
```

In another terminal, make sure the required model is installed:

```bash
ollama pull qwen3:4b
```

Ollama normally runs at:

```text
http://localhost:11434
```

## Run the application

Make sure the virtual environment is active and that you are in the project directory.

Recommended command:

```bash
python -m streamlit run app.py
```

Streamlit will display a local URL, normally:

```text
http://localhost:8501
```

Open that URL in a browser.

The following command is also valid after activating the correct virtual environment:

```bash
streamlit run app.py
```

If Python cannot find the local `interview_coach` package, use:

```bash
PYTHONPATH=src python -m streamlit run app.py
```

The `PYTHONPATH=src` option explicitly tells Python to use this project's local `src` directory.

## Run the provider self-test

The provider self-test checks configuration and provider initialization without sending a real model request.

Run:

```bash
PYTHONPATH=src python -m interview_coach.provider
```

The self-test:

- Loads the environment configuration.
- Prints the effective model priority.
- Initializes the provider.
- Confirms successful initialization.
- Does not consume model API credits.

## Run the automated tests

With the virtual environment active, run:

```bash
python -m pytest -q
```

The tests cover:

- Provider initialization.
- Model priority.
- Provider routing.
- Anthropic native Messages API routing.
- Gemini OpenAI-compatible routing.
- Ollama routing.
- Schema validation.
- Fallback behavior.
- Adaptive interview flow.
- Document and service behavior.

Most provider tests use mocked responses and do not consume API credits.

Some audio or local integration tests may be skipped when their optional dependencies or environment settings are unavailable.

## Typical interview flow

1. Start the Streamlit application.
2. Upload a resume or provide the required candidate information.
3. Paste or upload the job description.
4. Select the interview focus.
5. Generate a new interview.
6. Review the first interview question.
7. Record an answer.
8. Click **Save and analyze answer**.
9. Wait for transcription and analysis.
10. Review the analysis.
11. Answer the follow-up question if one is generated.
12. Continue until the interview advances to the next planned question.
13. Review the final interview results.

A sufficiently detailed answer may advance directly to the next question.

Every answer does not require a follow-up.

## Adaptive follow-up behavior

The application can generate three types of follow-up actions:

- Probe
- Clarification
- Challenge

A question can have a maximum of two follow-up questions.

Follow-up questions are labeled clearly in the interface, for example:

```text
Follow-up 1 of 2
```

A fresh microphone control is provided for each follow-up answer.

## Validation and retry behavior

The application validates model responses using defined schemas.

If question generation or answer analysis fails schema validation:

1. The provider makes one correction attempt using the same model.
2. If correction also fails, the next configured provider is tried.
3. If all providers fail, the current interview state is preserved.
4. The interface displays an error.
5. The saved recording and transcript can be retried.

The application validates:

- Required response fields.
- Valid analysis actions.
- Required follow-up questions for probe, clarification, and challenge actions.
- A missing question when the action is advance.
- Non-empty question lists.

Invalid model output cannot silently advance the interview.

Valid responses normally require only one model call.

## Provider API behavior

### Ollama

For Qwen3 running through local Ollama:

- Uses Ollama's native structured-output endpoint.
- Thinking is disabled for question generation and answer analysis.
- Generation is capped at 3,000 output tokens.
- Analysis is capped at 800 output tokens.
- Generation timeout is 180 seconds.
- Analysis timeout is 120 seconds.
- Uses a conservative context-size estimate.
- Rejects oversized input with a clear error.

### Gemini

Gemini uses an OpenAI-compatible client and request format.

### Anthropic

Anthropic uses the native Messages API.

The Anthropic request does not use the OpenAI chat-completions format.

## Audio and metadata

Audio files are saved locally using names such as:

```text
question_01.wav
question_01_followup_01.wav
question_01_followup_02.wav
```

Metadata includes:

- The actual question asked.
- The transcript.
- The model analysis.
- Processing status.
- Failure details.
- Follow-up information.

Audio, transcripts, and analysis are saved in:

```text
recordings/
```

## Security and privacy

Resume text, job-description text, transcripts, and analysis are held in memory during processing.

Depending on the configured provider:

- Ollama processes requests locally.
- Gemini receives selected content through Google's API.
- Anthropic receives selected content through Anthropic's API.

Do not commit any of the following:

- `.env`
- API keys
- Audio recordings
- Transcripts
- Candidate data
- Generated reports

The `.env.example` file is safe to commit only when it contains placeholder values and no real secrets.

Automatic data retention is not implemented yet.

## Project structure

```text
app.py                              Streamlit user interface

src/
└── interview_coach/
    ├── __init__.py                 Package initialization
    ├── config.py                   Environment and model configuration
    ├── document.py                 PDF, DOCX, and TXT extraction
    ├── prompt.py                   Prompt construction
    ├── provider.py                 LLM provider boundary and fallback
    ├── schemas.py                  Validated model response schemas
    ├── service.py                  Application workflow
    ├── recording.py                Audio and metadata storage
    ├── speech.py                   Text-to-speech support
    └── transcription.py            Speech-to-text support

tests/
├── test_provider.py                Provider behavior tests
├── test_adaptive_flow.py           Adaptive interview flow tests
├── test_document.py                Document extraction tests
├── test_schemas.py                 Schema validation tests
└── test_service.py                 Service behavior tests

.env.example                        Environment variable template
pyproject.toml                      Project and dependency configuration
requirements.txt                    Dependency list
README.md                           Project documentation
```

## Application flow

The main application flow is:

```text
User input
    ↓
Resume and job-description extraction
    ↓
Interview question generation
    ↓
Audio recording
    ↓
Speech-to-text transcription
    ↓
Answer analysis
    ↓
Follow-up question or next planned question
    ↓
Final interview results
```

## Troubleshooting

### ImportError involving `interview_coach`

Make sure you are running commands from the project directory and that the correct virtual environment is active.

Try:

```bash
source .venv/bin/activate
python -m pip install -e ".[dev]"
PYTHONPATH=src python -m streamlit run app.py
```

### Configuration error mentioning `MODEL_PRIORITY`

Make sure every provider listed in `MODEL_PRIORITY` is configured.

For example, if using:

```text
MODEL_PRIORITY=anthropic,gemini,ollama
```

check that:

- `ANTHROPIC_API_KEY` is available.
- `GEMINI_API_KEY` is available.
- Ollama is running.
- The required models are correctly named.

### Streamlit command is not found

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Then run:

```bash
python -m streamlit run app.py
```

### Ollama request fails

Check that Ollama is running:

```bash
ollama serve
```

Check that the model is installed:

```bash
ollama list
```

### Cloud provider request fails

Check:

- API key value.
- Model name.
- Base URL.
- Internet connection.
- Provider account access.
- Current provider priority.

## Current limitations

- Authentication is not implemented.
- Multi-user support is not implemented.
- Automatic retention and cleanup are not implemented.
- Candidate data is currently stored locally.
- Cloud provider usage may incur API costs.
- Provider response time depends on the selected model and network.
- Production deployment configuration is not included yet.
- Observability and centralized logging are not implemented yet.

## Development status

The current version includes:

- Three configurable model providers.
- Provider priority controlled through `.env`.
- Provider fallback.
- Native Anthropic Messages API integration.
- Gemini OpenAI-compatible integration.
- Native Ollama structured-output integration.
- Adaptive follow-up questions.
- Schema validation.
- Retry behavior.
- Local recording and transcription.
- Automated tests.
- Environment example configuration.

Production-level refactoring, authentication, deployment, data retention, and observability can be addressed in a later phase.