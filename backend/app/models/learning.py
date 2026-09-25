import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.catalog import UUIDTimestampMixin, User
from app.models.digital import Chapter


class QuizDifficulty(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class QuizGeneratedBy(str, enum.Enum):
    ADMIN = "ADMIN"
    AI = "AI"


class QuestionType(str, enum.Enum):
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"


class Quiz(UUIDTimestampMixin, Base):
    __tablename__ = "quizzes"

    chapter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chapters.id"), index=True)
    title: Mapped[str] = mapped_column(String)
    difficulty: Mapped[QuizDifficulty] = mapped_column(Enum(QuizDifficulty, name="quiz_difficulty"))
    generated_by: Mapped[QuizGeneratedBy] = mapped_column(
        Enum(QuizGeneratedBy, name="quiz_generated_by"),
        default=QuizGeneratedBy.ADMIN,
        server_default=QuizGeneratedBy.ADMIN.value,
    )
    ai_model: Mapped[Optional[str]] = mapped_column(String)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"), index=True)

    chapter: Mapped[Chapter] = relationship(back_populates="quizzes")
    creator: Mapped[Optional[User]] = relationship()
    questions: Mapped[list["QuizQuestion"]] = relationship(
        back_populates="quiz", cascade="all, delete-orphan", order_by="QuizQuestion.order_number"
    )
    attempts: Mapped[list["QuizAttempt"]] = relationship(back_populates="quiz")


class QuizQuestion(UUIDTimestampMixin, Base):
    __tablename__ = "quiz_questions"
    __table_args__ = (UniqueConstraint("quiz_id", "order_number"),)

    quiz_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quizzes.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type"),
        default=QuestionType.MULTIPLE_CHOICE,
        server_default=QuestionType.MULTIPLE_CHOICE.value,
    )
    order_number: Mapped[int] = mapped_column(Integer)

    quiz: Mapped[Quiz] = relationship(back_populates="questions")
    options: Mapped[list["QuizOption"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", order_by="QuizOption.order_number"
    )


class QuizOption(UUIDTimestampMixin, Base):
    __tablename__ = "quiz_options"
    __table_args__ = (UniqueConstraint("question_id", "order_number"),)

    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quiz_questions.id"), index=True)
    option_text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    order_number: Mapped[int] = mapped_column(Integer)

    question: Mapped[QuizQuestion] = relationship(back_populates="options")


class QuizAttempt(UUIDTimestampMixin, Base):
    __tablename__ = "quiz_attempts"

    quiz_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quizzes.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    score: Mapped[Optional[float]] = mapped_column(Float)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_questions: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    quiz: Mapped[Quiz] = relationship(back_populates="attempts")
    user: Mapped[User] = relationship(back_populates="quiz_attempts")
    answers: Mapped[list["QuizAnswer"]] = relationship(back_populates="attempt", cascade="all, delete-orphan")


class QuizAnswer(UUIDTimestampMixin, Base):
    __tablename__ = "quiz_answers"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id"),)

    attempt_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quiz_attempts.id"), index=True)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quiz_questions.id"), index=True)
    selected_option_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quiz_options.id"))
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)

    attempt: Mapped[QuizAttempt] = relationship(back_populates="answers")
    question: Mapped[QuizQuestion] = relationship()
    selected_option: Mapped[QuizOption] = relationship()
