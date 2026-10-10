import pytest
from pydantic import ValidationError

from interview_coach.schemas import AnswerAnalysis


def test_accepts_probe_with_follow_up_question() -> None:
    result = AnswerAnalysis(
        action="probe",
        answer_quality="partial",
        evidence_found="The candidate described the project goal.",
        missing_evidence="No personal contribution or measurable outcome.",
        reasoning="The answer needs more evidence of ownership and impact.",
        follow_up_question="What specifically did you do, and what was the result?",
    )

    assert result.action == "probe"


@pytest.mark.parametrize("action", ["probe", "clarify", "challenge", "advance"])
def test_accepts_all_supported_actions(action: str) -> None:
    follow_up = (
        "Can you explain that in more detail?"
        if action != "advance"
        else None
    )

    result = AnswerAnalysis(
        action=action,
        answer_quality="strong",
        evidence_found="Clear example with a measurable result.",
        missing_evidence="None.",
        reasoning="The answer provides sufficient evidence.",
        follow_up_question=follow_up,
    )

    assert result.action == action


def test_rejects_invalid_action() -> None:
    with pytest.raises(ValidationError):
        AnswerAnalysis(
            action="repeat",
            answer_quality="partial",
            evidence_found="Some evidence.",
            missing_evidence="More detail needed.",
            reasoning="The answer is incomplete.",
            follow_up_question="Can you explain further?",
        )


def test_rejects_invalid_answer_quality() -> None:
    with pytest.raises(ValidationError):
        AnswerAnalysis(
            action="probe",
            answer_quality="excellent",
            evidence_found="Some evidence.",
            missing_evidence="More detail needed.",
            reasoning="The answer is incomplete.",
            follow_up_question="Can you explain further?",
        )


def test_requires_follow_up_for_probe() -> None:
    with pytest.raises(
        ValueError,
        match="follow-up question is required",
    ):
        AnswerAnalysis(
            action="probe",
            answer_quality="weak",
            evidence_found="No concrete example.",
            missing_evidence="Specific actions and outcomes.",
            reasoning="The answer is too vague.",
        )


def test_rejects_follow_up_for_advance() -> None:
    with pytest.raises(
        ValueError,
        match="must not include",
    ):
        AnswerAnalysis(
            action="advance",
            answer_quality="strong",
            evidence_found="Clear example and measurable outcome.",
            missing_evidence="None.",
            reasoning="The answer is sufficient.",
            follow_up_question="What happened next?",
        )
