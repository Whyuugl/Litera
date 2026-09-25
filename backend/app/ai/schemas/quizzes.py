from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


class GeneratedOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=2000)
    is_correct: bool


class GeneratedQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=5000)
    question_type: Literal["MULTIPLE_CHOICE"]
    options: list[GeneratedOption] = Field(min_length=2, max_length=8)
    explanation: str = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def validate_options(self):
        if sum(option.is_correct for option in self.options) != 1:
            raise ValueError("Each question must have exactly one correct option")
        options = [_normalized(option.text) for option in self.options]
        if any(not option for option in options) or len(options) != len(set(options)):
            raise ValueError("Question options must be non-empty and unique")
        return self


class GeneratedQuiz(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    questions: list[GeneratedQuestion] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_questions(self):
        questions = [_normalized(question.question) for question in self.questions]
        if len(questions) != len(set(questions)):
            raise ValueError("Generated questions must be unique")
        return self
