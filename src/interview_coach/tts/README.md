# Interview question TTS

The existing `speech.render_question_speech([active_question])` forwards to
`tts/playback.py`. All new speech logic and tests live in this package.

## Configure

Edit `DEFAULT_PRIORITY` at the top of `config.py`, or override it in the environment:

```dotenv
TTS_PRIORITY=google,elevenlabs,azure,local,browser
```

Copy the TTS settings you need from the project's `.env.example` into your existing
`.env`, or set process environment variables. Restart after editing settings.
Environment settings take precedence over the defaults. Only listed providers are
attempted; duplicates are removed and `browser` is always last.
`TTS_PRIORITY=browser` selects browser speech alone, without cloud requests.

| Provider | Required settings | Setup |
| --- | --- | --- |
| ElevenLabs | `TTS_ELEVENLABS_API_KEY` | Voice and model defaults can be overridden. |
| Google Cloud | `TTS_GOOGLE_API_KEY` or `TTS_GOOGLE_ACCESS_TOKEN` | Enable Cloud Text-to-Speech and billing; optionally set `TTS_GOOGLE_PROJECT` for quota billing. OAuth tokens expire and must be refreshed externally. This does not reuse the Gemini key. |
| Azure | `TTS_AZURE_API_KEY`, `TTS_AZURE_REGION` | The Speech resource's key and matching region. |
| Local | `TTS_LOCAL_BASE_URL=http://127.0.0.1:8880/v1` | Separately install/run Kokoro-FastAPI and download its model. Only loopback URLs are accepted. |
| Browser | None | Device/browser must support `speechSynthesis`. |

Choose voices matching `TTS_LANGUAGE`; changing language does not automatically select
another voice. `TTS_SPEED` supports 0.7–1.2. Kokoro's language depends on its selected voice.
The defaults target English. No provider SDK or local model is installed automatically;
the REST adapters use the existing `httpx` library, now explicitly listed as a dependency.

## Playback, caching and fallback

- Audio is prepared when an active question is rendered. Read all, Stop and Replay selected
  use the generated audio. **Use browser voice** offers an immediate manual fallback.
- The first configured successful provider wins. Missing credentials are skipped. HTTP,
  quota, timeout, invalid audio and adapter errors fall through to the next provider.
- Failed providers have a 60-second session cooldown. The default request timeout is four
  seconds; an eight-second attempt budget stops starting additional requests after expiry.
  Socket/DNS behavior means this is not a strict wall-clock deadline. All are configurable.
- Playback decoding errors try browser speech. Blocked playback displays a retry message.
  When browser speech is unsupported, the on-screen question is still available.
- Cache is memory-only, per interview, bounded to 20 MiB/64 entries, with a one-hour TTL.
  Replay makes no new server request. Normal Streamlit reruns reuse cached audio. Refresh,
  restart, new interview, or changed configuration resets it; expiry/eviction can cause
  another paid generation. No disk cache or `.gitignore` change is needed.
- Each service has immutable configuration, so cached audio is specific to its priority,
  voices, models, language and speed. Browser results after failure expire with the cooldown.
- Inputs above 4,500 UTF-8 bytes use browser speech directly without truncation.
- Fallback may change the voice. Each uncached question follows the configured priority.
  Cloud providers receive question text. Billing/retention is controlled by their accounts;
  this package does not implement a monthly spending cap, autoplay or streaming conversation.

## Check and run

From the project root, check configuration without network requests or charges:

```bash
PYTHONPATH=src .venv/bin/python -m interview_coach.tts
```

Run an isolated sample-question demo (Prepare audio can consume provider credits):

```bash
PYTHONPATH=src .venv/bin/python -m streamlit run src/interview_coach/tts/demo.py
```

Prefix with `TTS_PRIORITY=browser` for a free browser-only test. Check Read all, Stop,
Replay selected and Use browser voice. No resume, question-generation model or microphone
is needed for this demo.

Automated tests use mocked HTTP and browser APIs without spending credits:

```bash
.venv/bin/python -m pytest -q src/interview_coach/tts/tests tests
node --test src/interview_coach/tts/tests/playback.test.mjs
```

The Python tests cover requests, failures, cache isolation and Streamlit integration.
The Node tests check playback lifecycle using browser stubs. Actual voice quality and
account access still require listening tests with configured providers.

API references: [ElevenLabs](https://elevenlabs.io/docs/api-reference/text-to-speech/convert),
[Google](https://cloud.google.com/text-to-speech/docs/reference/rest/v1/text/synthesize),
[Azure](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech),
[Kokoro-FastAPI](https://github.com/remsky/Kokoro-FastAPI).
