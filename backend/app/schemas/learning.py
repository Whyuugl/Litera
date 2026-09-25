import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import QuestionType, QuizDifficulty, QuizGeneratedBy


class OptionInput(BaseModel):
    option_text: str = Field(min_length=1, max_length=2000)
    is_correct: bool = False


class QuestionInput(BaseModel):
    question: str = Field(min_length=1, max_length=5000)
    explanation: str | None = Field(default=None, max_length=5000)
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE
    options: list[OptionInput] = Field(min_length=2)


class QuizCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    difficulty: QuizDifficulty = QuizDifficulty.MEDIUM
    is_published: bool = False
    questions: list[QuestionInput] = Field(min_length=1)


class QuizUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    difficulty: QuizDifficulty | None = None
    is_published: bool | None = None
    questions: list[QuestionInput] | None = Field(default=None, min_length=1)


class AdminOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    option_text: str
    is_correct: bool
    order_number: int


class AdminQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    question: str
    explanation: str | None
    question_type: QuestionType
    order_number: int
    options: list[AdminOptionResponse]


class AdminQuizResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    chapter_id: uuid.UUID
    title: str
    difficulty: QuizDifficulty
    generated_by: QuizGeneratedBy
    ai_model: str | None
    is_published: bool
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    questions: list[AdminQuestionResponse] = []
    attempt_count: int = 0


class StudentOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    option_text: str
    order_number: int


class StudentQuestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    question: str
    question_type: QuestionType
    order_number: int
    options: list[StudentOption]


class StudentQuiz(BaseModel):
    id: uuid.UUID
    chapter_id: uuid.UUID
    edition_id: uuid.UUID
    title: str
    difficulty: QuizDifficulty
    questions: list[StudentQuestion]


class QuizSummary(BaseModel):
    id: uuid.UUID
    chapter_id: uuid.UUID
    title: str
    difficulty: QuizDifficulty
    question_count: int


class AttemptStarted(BaseModel):
    id: uuid.UUID
    quiz: StudentQuiz
    started_at: datetime
    answers: dict[uuid.UUID, uuid.UUID] = {}


class AnswerSelection(BaseModel):
    selected_option_id: uuid.UUID


class AnswerSaved(BaseModel):
    question_id: uuid.UUID
    selected_option_id: uuid.UUID


class AttemptSummary(BaseModel):
    id: uuid.UUID
    quiz_id: uuid.UUID
    score: float | None
    correct_answers: int
    total_questions: int
    started_at: datetime
    completed_at: datetime | None


class AnswerReview(BaseModel):
    question_id: uuid.UUID
    question: str
    selected_option_id: uuid.UUID
    selected_answer: str
    correct_option_id: uuid.UUID
    correct_answer: str
    is_correct: bool
    explanation: str | None


class AttemptResult(AttemptSummary):
    quiz: StudentQuiz
    review: list[AnswerReview]


class LearningChapter(BaseModel):
    id: uuid.UUID
    chapter_number: int
    title: str
    page_start: int
    page_end: int
    is_read: bool
    quizzes: list[QuizSummary]
    best_score: float | None
    summary_available: bool


class LearningProgress(BaseModel):
    edition_id: uuid.UUID
    book: dict
    chapters_total: int
    chapters_read: int
    quizzes_available: int
    quizzes_completed: int
    average_score: float | None
    book_summary_available: bool
    chapters: list[LearningChapter]
