import json
from collections import deque

import httpx
import pytest
from openai import OpenAI

from interview_coach.config import ModelCandidate, Settings
from interview_coach.provider import OpenAIQuestionProvider, ProviderError
from interview_coach.schemas import AnswerAnalysis, InterviewQuestionSet

REQUEST = {
    "question": "What did you improve?",
    "answer": "I improved onboarding.",
    "resume_text": "Product manager.",
    "job_description": "Improve onboarding.",
    "competency": "Ownership",
    "experience_level": "senior",
    "follow_up_count": 0,
    "max_follow_ups": 2,
    "total_questions_asked": 1,
}
RESULT = {
    "action": "probe",
    "answer_quality": "partial",
    "evidence_found": "Onboarding claim.",
    "missing_evidence": "Personal contribution.",
    "reasoning": "Need details.",
    "follow_up_question": "What did you personally change?",
}


@pytest.fixture
def client_factory():
    opened = []
    OpenAIQuestionProvider._unhealthy_until.clear()

    def build(responses, local=False):
        candidates = tuple(
            ModelCandidate(
                name=f"Model {i}",
                model="qwen3:4b",
                api_key="test-key",
                base_url=f"http://localhost:{11434 + i}/v1/"
                if local
                else f"http://model-{i}.invalid/v1/",
            )
            for i in range(len(responses))
        )
        provider = OpenAIQuestionProvider(Settings(candidates=candidates))
        calls = []
        for candidate, response in zip(candidates, responses, strict=True):
            provider._clients[candidate].close()
            sequence = deque(response) if isinstance(response, list) else None

            def handler(request, response=response, sequence=sequence):
                calls.append(json.loads(request.content))
                if sequence is not None:
                    assert sequence, "Unexpected extra model call"
                    response = sequence.popleft()
                if isinstance(response, Exception):
                    raise response
                if isinstance(response, int):
                    return httpx.Response(response, json={"error": {"message": "Unavailable"}})
                if request.url.path == "/api/chat" and "choices" in response:
                    response = {
                        "done": True,
                        "done_reason": "stop",
                        "message": response["choices"][0]["message"],
                    }
                return httpx.Response(200, json=response)

            client = OpenAI(
                api_key=candidate.api_key,
                base_url=candidate.base_url,
                max_retries=0,
                http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            )
            provider._clients[candidate] = client
            opened.append(client)
        return provider, calls

    yield build
    for client in opened:
        client.close()
    OpenAIQuestionProvider._unhealthy_until.clear()


def completion(result=RESULT, refusal=None):
    return {
        "id": "test",
        "created": 0,
        "model": "qwen3:4b",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": json.dumps(result),
                    "refusal": refusal,
                },
            }
        ],
    }


def test_actual_sdk_parses_answer_schema(client_factory):
    provider, calls = client_factory([completion()])
    result = provider.analyze_answer(**REQUEST)
    assert isinstance(result, AnswerAnalysis)
    assert result.action == "probe"
    assert calls[0]["response_format"]["json_schema"]["name"] == "AnswerAnalysis"
    assert calls[0]["max_tokens"] == 800


def test_local_qwen_disables_thinking_at_api_level(client_factory):
    provider, calls = client_factory([completion()], local=True)
    provider.analyze_answer(**REQUEST)
    assert calls[0]["think"] is False
    assert calls[0]["options"] == {"num_ctx": 8192, "num_predict": 800, "temperature": 0}
    assert calls[0]["format"]["title"] == "AnswerAnalysis"


@pytest.mark.parametrize("action", ["probe", "clarify", "challenge", "advance"])
def test_local_schema_enforces_action_followup_pair(client_factory, action):
    from jsonschema import Draft202012Validator

    model, calls = client_factory([completion()], local=True)
    model.analyze_answer(**REQUEST)
    validator = Draft202012Validator(calls[0]["format"])
    valid = {
        **RESULT,
        "action": action,
        "follow_up_question": None if action == "advance" else "What did you change?",
    }
    assert validator.is_valid(valid)
    invalid = {**valid, "follow_up_question": "What changed?" if action == "advance" else None}
    assert not validator.is_valid(invalid)
    assert not validator.is_valid({k: v for k, v in valid.items() if k != "follow_up_question"})


@pytest.mark.parametrize("failure", [429, 503, httpx.ConnectError("Connection refused")])
def test_analysis_fails_over_on_outage(client_factory, failure):
    provider, calls = client_factory([failure, completion()])
    assert provider.analyze_answer(**REQUEST).action == "probe"
    assert len(calls) == 2


@pytest.mark.parametrize(
    ("response", "expected_calls"),
    [
        (completion({**RESULT, "follow_up_question": None}), 2),
        (completion({**RESULT, "action": "invalid"}), 2),
        (completion(refusal="Sensitive refusal text"), 1),
        ({**completion(), "choices": []}, 1),
        (401, 1),
    ],
)
def test_invalid_result_does_not_silently_advance_or_fail_over(
    client_factory,
    response,
    expected_calls,
):
    provider, calls = client_factory([response, completion()])
    with pytest.raises(ProviderError) as error:
        provider.analyze_answer(**REQUEST)
    assert len(calls) == expected_calls
    assert all(
        call["messages"][0]["content"] == calls[0]["messages"][0]["content"] for call in calls
    )
    assert "Sensitive refusal text" not in str(error.value)
    assert REQUEST["answer"] not in str(error.value)


@pytest.mark.parametrize(
    "invalid",
    [
        {**RESULT, "follow_up_question": None},
        {**RESULT, "action": "advance"},
        {**RESULT, "evidence_found": ["Onboarding claim."]},
        {**RESULT, "missing_evidence": None},
        {**RESULT, "answer_quality": "excellent"},
    ],
)
def test_repairs_invalid_response_once_on_same_model(client_factory, invalid):
    model, calls = client_factory([[completion(invalid), completion()]])
    result = model.analyze_answer(**REQUEST)
    assert result.action == "probe"
    assert result.follow_up_question == RESULT["follow_up_question"]
    assert len(calls) == 2
    assert "failed schema validation" in calls[1]["messages"][-1]["content"]
    assert calls[1]["messages"][:2] == calls[0]["messages"]


def test_exhausted_repair_logs_field_types_without_sensitive_values(client_factory, caplog):
    invalid = {
        **RESULT,
        "answer_quality": "private-invalid-value",
        "reasoning": ["private-details"],
    }
    model, calls = client_factory([completion(invalid)])
    with pytest.raises(ProviderError, match="after one repair") as error:
        model.analyze_answer(**REQUEST)
    assert len(calls) == 2
    assert "answer_quality: literal_error" in str(error.value)
    assert "reasoning: string_type" in str(error.value)
    assert "private-invalid-value" not in caplog.text + str(error.value)
    assert "private-details" not in caplog.text + str(error.value)
    assert "private-details" not in calls[1]["messages"][-1]["content"]


def test_malformed_json_is_repaired(client_factory):
    malformed = completion()
    malformed["choices"][0]["message"]["content"] = "not valid json"
    model, calls = client_factory([[malformed, completion()]])
    assert model.analyze_answer(**REQUEST).action == "probe"
    assert len(calls) == 2


QUESTION_SET = {
    "summary": "Assess ownership and payments experience.",
    "questions": [
        {
            "question": "Describe a payments improvement you led.",
            "competency": "Ownership",
            "difficulty": "advanced",
            "source_focus": "both",
            "rationale": "The role involves payments.",
            "expected_evidence": "Personal actions, trade-offs and impact.",
        }
    ],
}


@pytest.mark.parametrize("local", [False, True])
def test_generation_repairs_empty_questions_once(client_factory, local):
    empty = {"summary": "private model explanation", "questions": []}
    model, calls = client_factory([[completion(empty), completion(QUESTION_SET)]], local=local)
    result = model.generate("Payments product manager.", "Lead payments products.")
    assert len(result.questions) == 1
    assert len(calls) == 2
    assert "questions: too_short" in calls[1]["messages"][-1]["content"]
    assert "private model explanation" not in calls[1]["messages"][-1]["content"]
    if local:
        assert calls[0]["think"] is False
        assert calls[0]["format"]["properties"]["questions"]["minItems"] == 1
        assert calls[0]["options"]["num_predict"] == 3000
    else:
        schema = calls[0]["response_format"]["json_schema"]["schema"]
        assert schema["properties"]["questions"]["minItems"] == 1


def test_generation_exhausts_repair_without_raw_error_or_fallback(client_factory, caplog):
    empty = {"summary": "private model explanation", "questions": []}
    model, calls = client_factory([completion(empty), completion(QUESTION_SET)])
    with pytest.raises(ProviderError, match="after one repair") as error:
        model.generate("Private candidate resume.", "Private job description.")
    assert len(calls) == 2
    assert "private model explanation" not in str(error.value) + caplog.text
    assert "input_value" not in str(error.value)


@pytest.mark.parametrize("operation", ["generate", "analyze"])
def test_local_long_documents_use_larger_context(client_factory, operation):
    model, calls = client_factory(
        [completion(QUESTION_SET if operation == "generate" else RESULT)], local=True
    )
    long_resume = "Relevant work experience. " * 600
    if operation == "generate":
        model.generate(long_resume, "Lead payments products.")
    else:
        model.analyze_answer(**{**REQUEST, "resume_text": long_resume})
    assert calls[0]["options"]["num_ctx"] == 16384


def test_oversized_input_stops_before_local_call(client_factory):
    model, calls = client_factory([completion(QUESTION_SET)], local=True)
    with pytest.raises(ProviderError, match="too long"):
        model.generate("x" * 40000, "Payments role.")
    assert not calls


def test_local_truncated_generation_is_repaired(client_factory):
    truncated = {"done": True, "done_reason": "length", "message": {"content": "{}"}}
    model, calls = client_factory([[truncated, completion(QUESTION_SET)]], local=True)
    assert model.generate("Resume", "Job description").questions
    assert len(calls) == 2


def test_question_schema_rejects_empty_list():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        InterviewQuestionSet.model_validate({"summary": "Focus", "questions": []})


@pytest.mark.parametrize("failure", [429, 503, httpx.ConnectError("Connection refused")])
def test_generation_fails_over_on_outage(client_factory, failure):
    model, calls = client_factory([failure, completion(QUESTION_SET)])
    assert model.generate("Resume", "Job description").questions
    assert len(calls) == 2
