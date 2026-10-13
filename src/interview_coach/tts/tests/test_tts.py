import base64
import json
import os
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock
from xml.etree.ElementTree import fromstring

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from interview_coach.tts import TTSConfig, TTSService, playback
from interview_coach.tts import cache as cache_module
from interview_coach.tts import service as service_module
from interview_coach.tts.cache import AudioCache
from interview_coach.tts.contracts import AudioResult, TTSError
from interview_coach.tts.providers import _http, build_providers

MP3 = b"ID3" + b"\x00" * 32


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for key in tuple(os.environ):
        if key.startswith("TTS_"):
            monkeypatch.delenv(key)
    monkeypatch.setattr(
        httpx, "stream", Mock(side_effect=AssertionError("Unexpected network call"))
    )


def fake_provider(name, *, error=None, configured=True):
    provider = Mock()
    provider.is_configured.return_value = configured
    provider.synthesize.side_effect = error
    provider.synthesize.return_value = AudioResult(name, MP3)
    return provider


def test_priority_can_be_reordered_but_browser_is_always_last():
    cfg = TTSConfig.from_env({"TTS_PRIORITY": "azure,browser,google,azure"})
    assert cfg.priority == ("azure", "google", "browser")
    assert TTSConfig.from_env({"TTS_PRIORITY": "browser"}).priority == ("browser",)
    assert TTSConfig.from_env({"TTS_SPEED": "1.1"}).speed == 1.1


@pytest.mark.parametrize(
    "env",
    [
        {"TTS_PRIORITY": "typo"},
        {"TTS_SPEED": "0"},
        {"TTS_SPEED": "nan"},
        {"TTS_TIMEOUT_SECONDS": "0"},
        {"TTS_COOLDOWN_SECONDS": "inf"},
        {"TTS_CACHE_MAX_BYTES": "-1"},
        {"TTS_MAX_INPUT_BYTES": "0"},
    ],
)
def test_bad_configuration_is_rejected(env):
    with pytest.raises(ValueError):
        TTSConfig.from_env(env)


def test_priority_success_stops_requests_and_caches_replay():
    azure, google = fake_provider("azure"), fake_provider("google")
    service = TTSService(
        TTSConfig(priority=("azure", "google")), {"azure": azure, "google": google}
    )
    assert service.synthesize("Question?").provider == "azure"
    assert service.synthesize("Question?").provider == "azure"
    assert azure.synthesize.call_count == 1
    google.synthesize.assert_not_called()


@pytest.mark.parametrize("error", [TTSError("quota"), TimeoutError(), RuntimeError("secret")])
def test_failure_falls_through_and_cooldown_prevents_repeated_calls(error, caplog):
    first, second = fake_provider("elevenlabs", error=error), fake_provider("google")
    service = TTSService(TTSConfig(), {"elevenlabs": first, "google": second})
    assert service.synthesize("Private candidate question?").provider == "google"
    assert service.synthesize("Another question?").provider == "google"
    assert first.synthesize.call_count == 1
    assert "secret" not in caplog.text and "Private candidate" not in caplog.text


def test_unconfigured_and_failed_providers_end_at_browser():
    first = fake_provider("elevenlabs", configured=False)
    second = fake_provider("google", error=TTSError("unavailable"))
    service = TTSService(TTSConfig(), {"elevenlabs": first, "google": second})
    assert service.synthesize("Question?").is_browser
    first.synthesize.assert_not_called()
    assert TTSService(TTSConfig.from_env({})).synthesize("Question?").is_browser


def test_budget_prevents_starting_more_requests(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(service_module, "monotonic", lambda: clock[0])
    first, second = fake_provider("elevenlabs"), fake_provider("google")

    def fail(*args):
        clock[0] = 9
        raise TTSError("timeout")

    first.synthesize.side_effect = fail
    service = TTSService(TTSConfig(), {"elevenlabs": first, "google": second})
    assert service.synthesize("Question?").is_browser
    second.synthesize.assert_not_called()


def test_recovery_after_browser_result_expires(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(service_module, "monotonic", lambda: clock[0])
    monkeypatch.setattr(cache_module, "monotonic", lambda: clock[0])
    provider = fake_provider("elevenlabs", error=TTSError("temporary"))
    service = TTSService(TTSConfig(), {"elevenlabs": provider})
    assert service.synthesize("Question?").is_browser
    provider.synthesize.side_effect = None
    assert service.synthesize("Question?").is_browser
    clock[0] = 61
    assert service.synthesize("Question?").provider == "elevenlabs"


def test_cache_is_bounded_and_isolated():
    cache = AudioCache(len(MP3), max_entries=2)
    cache.put("one", AudioResult("google", MP3))
    cache.put("two", AudioResult("google", MP3))
    assert cache.get("one") is None
    assert cache.get("two").audio == MP3
    assert AudioCache(len(MP3)).get("two") is None
    cache.put("expired", AudioResult("browser"), ttl=-1)
    assert cache.get("expired") is None


def test_oversize_or_blank_input_never_calls_provider():
    provider = fake_provider("google")
    service = TTSService(TTSConfig(priority=("google",), max_input_bytes=5), {"google": provider})
    assert service.synthesize(" ").is_browser
    assert service.synthesize("नमस्ते").is_browser
    provider.synthesize.assert_not_called()


@pytest.fixture
def http_mock(monkeypatch):
    calls = []
    reply = {"status": 200, "body": MP3}

    def handle(request):
        calls.append(request)
        if "error" in reply:
            raise reply["error"]
        return httpx.Response(reply["status"], content=reply["body"])

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        monkeypatch.setattr(_http.httpx, "stream", client.stream)
        yield calls, reply


def provider_config():
    return TTSConfig(
        elevenlabs_api_key="test-key",
        google_api_key="test-key",
        azure_api_key="test-key",
        azure_region="eastus",
        local_base_url="http://127.0.0.1:8880/v1",
    )


@pytest.mark.parametrize("name", ["elevenlabs", "google", "azure", "local"])
def test_provider_request_and_audio_response(name, http_mock):
    calls, reply = http_mock
    if name == "google":
        reply["body"] = json.dumps({"audioContent": base64.b64encode(MP3).decode()}).encode()
    provider = build_providers(provider_config())[name]
    assert provider.is_configured()
    result = provider.synthesize("Explain A&B <tradeoffs>.", 2)
    assert result.audio == MP3 and result.provider == name
    request = calls[0]
    assert "test-key" not in str(request.url)
    if name == "azure":
        assert request.headers["Ocp-Apim-Subscription-Key"] == "test-key"
        assert "Explain A&B <tradeoffs>." in "".join(fromstring(request.content).itertext())
    else:
        body = json.loads(request.content)
        if name == "google":
            assert body["input"]["text"] == "Explain A&B <tradeoffs>."
            assert body["audioConfig"]["speakingRate"] == 0.92
            assert request.headers["x-goog-api-key"] == "test-key"
        elif name == "elevenlabs":
            assert body["voice_settings"]["speed"] == 0.92
            assert request.headers["xi-api-key"] == "test-key"
        else:
            assert body["input"] == "Explain A&B <tradeoffs>."
            assert request.url.path == "/v1/audio/speech"


@pytest.mark.parametrize("status", [401, 403, 429, 500, 302])
def test_http_failures_use_browser_without_leaking_response(status, http_mock, caplog):
    calls, reply = http_mock
    reply.update(status=status, body=b"private-error-body")
    cfg = replace(provider_config(), priority=("elevenlabs",))
    assert TTSService(cfg).synthesize("Question?").is_browser
    assert len(calls) == 1
    assert "private-error-body" not in caplog.text


@pytest.mark.parametrize(
    "body", [b"", b"{}", b'{"audioContent":"!"}', b"null", b"<html>error</html>"]
)
def test_malformed_google_audio_falls_back(body, http_mock):
    _, reply = http_mock
    reply["body"] = body
    assert TTSService(replace(provider_config(), priority=("google",))).synthesize("Q?").is_browser


def test_timeout_and_invalid_audio_fall_back(http_mock):
    _, reply = http_mock
    cfg = replace(provider_config(), priority=("elevenlabs",))
    reply["error"] = httpx.ReadTimeout("private-key")
    assert TTSService(cfg).synthesize("Q?").is_browser
    reply.pop("error")
    reply["body"] = b'{"error":"not audio"}'
    assert TTSService(cfg).synthesize("Q?").is_browser


def test_google_oauth_and_quota_project(http_mock):
    calls, reply = http_mock
    reply["body"] = json.dumps({"audioContent": base64.b64encode(MP3).decode()}).encode()
    cfg = replace(provider_config(), google_access_token="test-token", google_project="project")
    build_providers(cfg)["google"].synthesize("Q?", 2)
    assert calls[0].headers["Authorization"] == "Bearer test-token"
    assert calls[0].headers["x-goog-user-project"] == "project"
    assert "x-goog-api-key" not in calls[0].headers
    assert "test-token" not in repr(cfg) and "test-key" not in repr(cfg)


@pytest.mark.parametrize(
    "url", ["", "https://example.com/v1", "file:///tmp", "http://user@localhost/v1"]
)
def test_local_requires_explicit_loopback_server(url):
    assert not build_providers(TTSConfig(local_base_url=url))["local"].is_configured()


def test_playback_cache_resets_on_new_session_or_config(monkeypatch):
    state = {"interview_session_id": "first"}
    monkeypatch.setattr(playback.st, "session_state", state)
    component = Mock()
    monkeypatch.setattr(playback, "_SPEECH", component)
    provider = fake_provider("elevenlabs")
    monkeypatch.setattr(service_module, "build_providers", lambda config: {"elevenlabs": provider})
    playback.render_question_speech(["Question?"])
    playback.render_question_speech(["Question?"])
    assert provider.synthesize.call_count == 1
    assert component.call_args.kwargs["data"]["audio"][0].startswith("data:audio/mpeg;base64,")
    state["interview_session_id"] = "second"
    playback.render_question_speech(["Question?"])
    assert provider.synthesize.call_count == 2
    monkeypatch.setenv("TTS_SPEED", "1.1")
    playback.render_question_speech(["Question?"])
    assert provider.synthesize.call_count == 3
    monkeypatch.setenv("TTS_PRIORITY", "typo")
    playback.render_question_speech(["Question?"])
    assert component.call_args.kwargs["data"]["audio"] == [None]


def test_standalone_streamlit_demo_renders_and_reruns(monkeypatch):
    monkeypatch.setenv("TTS_PRIORITY", "browser")
    demo = Path(playback.__file__).with_name("demo.py")
    app = AppTest.from_file(str(demo)).run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state["_tts_state"][2].config.priority == ("browser",)
    app.run()
    assert not app.exception
