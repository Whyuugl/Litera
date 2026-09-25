"""phase 8 learning quizzes

Revision ID: a81e04c73b52
Revises: d42af61c908e
Create Date: 2026-09-25 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a81e04c73b52"
down_revision: Union[str, None] = "d42af61c908e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    difficulty = postgresql.ENUM("EASY", "MEDIUM", "HARD", name="quiz_difficulty", create_type=False)
    generated_by = postgresql.ENUM("ADMIN", "AI", name="quiz_generated_by", create_type=False)
    question_type = postgresql.ENUM("MULTIPLE_CHOICE", name="question_type", create_type=False)
    for enum in (difficulty, generated_by, question_type):
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "quizzes",
        sa.Column("chapter_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("difficulty", difficulty, nullable=False),
        sa.Column("generated_by", generated_by, server_default="ADMIN", nullable=False),
        sa.Column("ai_model", sa.String(), nullable=True),
        sa.Column("is_published", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quizzes_chapter_id", "quizzes", ["chapter_id"])
    op.create_index("ix_quizzes_created_by", "quizzes", ["created_by"])
    op.create_table(
        "quiz_questions",
        sa.Column("quiz_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("question_type", question_type, server_default="MULTIPLE_CHOICE", nullable=False),
        sa.Column("order_number", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quiz_id", "order_number"),
    )
    op.create_index("ix_quiz_questions_quiz_id", "quiz_questions", ["quiz_id"])
    op.create_table(
        "quiz_options",
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("option_text", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("order_number", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["quiz_questions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", "order_number"),
    )
    op.create_index("ix_quiz_options_question_id", "quiz_options", ["question_id"])
    op.create_table(
        "quiz_attempts",
        sa.Column("quiz_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("correct_answers", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quiz_attempts_quiz_id", "quiz_attempts", ["quiz_id"])
    op.create_index("ix_quiz_attempts_user_id", "quiz_attempts", ["user_id"])
    op.create_table(
        "quiz_answers",
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("selected_option_id", sa.Uuid(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["quiz_attempts.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["quiz_questions.id"]),
        sa.ForeignKeyConstraint(["selected_option_id"], ["quiz_options.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id", "question_id"),
    )
    op.create_index("ix_quiz_answers_attempt_id", "quiz_answers", ["attempt_id"])
    op.create_index("ix_quiz_answers_question_id", "quiz_answers", ["question_id"])


def downgrade() -> None:
    for table in ("quiz_answers", "quiz_attempts", "quiz_options", "quiz_questions", "quizzes"):
        op.drop_table(table)
    for name in ("question_type", "quiz_generated_by", "quiz_difficulty"):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
