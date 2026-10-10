import pytest

from interview_coach.schemas import AnswerAnalysis, InterviewQuestion, InterviewQuestionSet
from interview_coach.service import AdaptiveInterviewService, InterviewQuestionService


class FakeProvider:
    def __init__(self) -> None:
        self.called = False

    def generate(self, resume_text: str, job_description: str) -> InterviewQuestionSet:
        self.called = True
        question = InterviewQuestion(
            question="Describe a relevant project.",
            competency="Relevant experience",
            difficulty="introductory",
            source_focus="both",
            rationale="Connects candidate evidence with the role.",
            expected_evidence="Specific actions, decisions, and outcomes.",
        )
        return InterviewQuestionSet(summary="Assess role fit.", questions=[question] * 10)

    def analyze_answer(self, **kwargs: str | int) -> AnswerAnalysis:
        return AnswerAnalysis(
            action="probe",
            answer_quality="partial",
            evidence_found="The answer names a process improvement.",
            missing_evidence="No specific action or measurable outcome.",
            reasoning="The answer needs concrete evidence.",
            follow_up_question="What specifically did you change, and what was the result?",
        )


def test_service_uses_provider_for_valid_inputs() -> None:
    provider = FakeProvider()
    service = InterviewQuestionService(provider)

    result = service.generate("r" * 100, "j" * 100)

    assert provider.called is True
    assert len(result.questions) == 10


def test_adaptive_service_uses_provider_for_answer_analysis() -> None:
    analysis = AdaptiveInterviewService(FakeProvider()).analyze_answer(
        question="Tell me about a difficult project.",
        answer="I improved the process.",
        resume_text="r" * 100,
        job_description="j" * 100,
        competency="Problem solving",
        experience_level="senior",
        follow_up_count=0,
        max_follow_ups=2,
        total_questions_asked=1,
    )

    assert analysis.action == "probe"


def test_adaptive_service_ends_at_global_question_limit() -> None:
    analysis = AdaptiveInterviewService(FakeProvider()).analyze_answer(
        question="Tell me about a difficult project.",
        answer="I improved the process.",
        resume_text="r" * 100,
        job_description="j" * 100,
        competency="Problem solving",
        experience_level="senior",
        follow_up_count=0,
        max_follow_ups=2,
        total_questions_asked=10,
    )

    assert analysis.action == "advance"
    assert analysis.follow_up_question is None


@pytest.mark.parametrize(
    ("resume_text", "job_description", "message"),
    [
        ("short", "j" * 100, "resume"),
        ("r" * 100, "short", "job description"),
    ],
)
def test_service_rejects_inputs_without_enough_text(
    resume_text: str, job_description: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        InterviewQuestionService(FakeProvider()).generate(resume_text, job_description)
