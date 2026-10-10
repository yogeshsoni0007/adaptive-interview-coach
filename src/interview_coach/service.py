from __future__ import annotations

from interview_coach.prompt import INTRODUCTION_QUESTION, MAX_TOTAL_QUESTIONS
from interview_coach.provider import QuestionProvider
from interview_coach.schemas import AnswerAnalysis, InterviewQuestionSet


class InterviewQuestionService:
    def __init__(self, provider: QuestionProvider) -> None:
        self._provider = provider

    def generate(self, resume_text: str, job_description: str) -> InterviewQuestionSet:
        if len(resume_text.strip()) < 100:
            raise ValueError(
                "The resume does not contain enough text to generate grounded questions."
            )
        if len(job_description.strip()) < 100:
            raise ValueError(
                "The job description does not contain enough text to generate grounded questions."
            )
        return self._provider.generate(resume_text, job_description)


class AdaptiveInterviewService:
    """Coordinate answer analysis without deciding how the UI stores state."""

    def __init__(self, provider: QuestionProvider) -> None:
        self._provider = provider

    def analyze_answer(
        self,
        *,
        question: str,
        answer: str,
        resume_text: str,
        job_description: str,
        competency: str,
        experience_level: str,
        follow_up_count: int,
        max_follow_ups: int,
        total_questions_asked: int,
        previous_context: str = "",
    ) -> AnswerAnalysis:
        if not answer.strip():
            raise ValueError("No transcript is available. Record your answer again.")
        if follow_up_count < 0 or max_follow_ups < 0:
            raise ValueError("Follow-up counts cannot be negative.")
        if not 1 <= total_questions_asked <= MAX_TOTAL_QUESTIONS:
            raise ValueError(
                f"Total questions asked must be between 1 and {MAX_TOTAL_QUESTIONS}."
            )

        analysis = self._provider.analyze_answer(
            question=question,
            answer=answer,
            resume_text=resume_text,
            job_description=job_description,
            competency=competency,
            experience_level=experience_level,
            follow_up_count=follow_up_count,
            max_follow_ups=max_follow_ups,
            total_questions_asked=total_questions_asked,
            previous_context=previous_context,
        )

        is_introduction = (
            question.strip().casefold() == INTRODUCTION_QUESTION.casefold()
            or competency.strip().casefold() == "introduction"
        )
        effective_max_follow_ups = min(max_follow_ups, 1) if is_introduction else max_follow_ups

        # Enforce the global interview budget even if the model ignores the prompt.
        if total_questions_asked >= MAX_TOTAL_QUESTIONS and analysis.action != "advance":
            analysis = analysis.model_copy(
                update={
                    "action": "advance",
                    "follow_up_question": None,
                    "reasoning": (
                        analysis.reasoning
                        + " Global question limit reached; ending interview."
                    ),
                }
            )
        # Enforce the per-topic follow-up limit even if the model ignores the prompt.
        elif follow_up_count >= effective_max_follow_ups and analysis.action != "advance":
            analysis = analysis.model_copy(
                update={
                    "action": "advance",
                    "follow_up_question": None,
                    "reasoning": analysis.reasoning + " Follow-up limit reached; moving on.",
                }
            )
        return analysis
