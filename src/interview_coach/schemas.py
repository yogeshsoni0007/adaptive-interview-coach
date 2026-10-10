from typing import Literal

from pydantic import BaseModel, Field, model_validator


class InterviewQuestion(BaseModel):
    question: str = Field(description="A concise interview question addressed to the candidate.")
    competency: str = Field(description="The primary competency tested by the question.")
    difficulty: Literal["introductory", "intermediate", "advanced"]
    source_focus: Literal["resume", "job_description", "both"]
    rationale: str = Field(description="Why this question is relevant for this role and candidate.")
    expected_evidence: str = Field(description="What a strong answer should demonstrate.")


class InterviewQuestionSet(BaseModel):
    summary: str = Field(description="A short summary of the recommended interview focus.")
    questions: list[InterviewQuestion] = Field(
        min_length=1,
        description="The interview questions. Generate ten; never return an empty list.",
    )


class AnswerAnalysis(BaseModel):
    action: Literal["probe", "clarify", "challenge", "advance"]
    answer_quality: Literal["weak", "partial", "strong"]
    evidence_found: str = Field(description="Specific evidence found in the candidate's answer.")
    missing_evidence: str = Field(
        description="Important evidence or detail missing from the answer."
    )
    reasoning: str = Field(
        description="Why this action and answer-quality classification were selected."
    )
    follow_up_question: str | None = Field(
        default=None,
        description=(
            "For probe, clarify, or challenge: one nonblank follow-up question. "
            "For advance: JSON null, never a question or the string 'null'."
        ),
    )

    @model_validator(mode="after")
    def validate_follow_up_question(self) -> "AnswerAnalysis":
        if self.action in {"probe", "clarify", "challenge"} and (
            not self.follow_up_question or not self.follow_up_question.strip()
        ):
            raise ValueError("A follow-up question is required for this action.")

        if self.action == "advance" and self.follow_up_question and self.follow_up_question.strip():
            raise ValueError("Advance action must not include a follow-up question.")

        return self
