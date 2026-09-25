import json
import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-characters"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.ai.providers.base import AIProviderError, GeneratedText, LLMProvider
from app.ai.services.quiz_generation_service import MAX_QUIZ_SOURCE_CHARS, _representative_source
from app.core.database import Base, get_session
from app.core.security import create_access_token
from app.main import app
from app.models import (
    Book,
    BookStatus,
    BookType,
    Category,
    Chapter,
    DigitalFile,
    DocumentPage,
    Edition,
    Membership,
    MembershipStatus,
    ProcessingStatus,
    Quiz,
    QuizAttempt,
    QuizGeneratedBy,
    QuizOption,
    QuizQuestion,
    User,
    UserRole,
)


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


def test_session():
    with Session(engine, expire_on_commit=False) as session:
        yield session


def quiz_json(count: int = 3, *, correct: int = 1, duplicate_options: bool = False) -> str:
    questions = []
    for index in range(count):
        options = [
            {"text": f"Correct concept {index}", "is_correct": correct > 0},
            {"text": f"Distractor {index}" if not duplicate_options else f"Correct concept {index}", "is_correct": correct > 1},
            {"text": f"Alternative {index}", "is_correct": False},
        ]
        questions.append({
            "question": f"What does grounded concept {index} explain?",
            "question_type": "MULTIPLE_CHOICE",
            "options": options,
            "explanation": f"The chapter explicitly explains grounded concept {index}.",
        })
    return json.dumps({"title": "AI Chapter Review", "questions": questions})


class FakeQuizProvider(LLMProvider):
    name = "fake"
    model = "fake-quiz-1"

    def __init__(self, content: str | None = None, *, fail: bool = False):
        self.content = content or quiz_json()
        self.fail = fail
        self.calls: list[tuple[str, str]] = []

    async def generate(self, system: str, prompt: str) -> GeneratedText:
        self.calls.append((system, prompt))
        if self.fail:
            raise AIProviderError("provider unavailable")
        return GeneratedText(self.content, 120, 80)


class QuizGenerationApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        app.dependency_overrides[get_session] = test_session
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        cls.client.__exit__(None, None, None)
        engine.dispose()

    def setUp(self) -> None:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        now = datetime.now(timezone.utc)
        with Session(engine, expire_on_commit=False) as session:
            self.admin = User(name="Admin", email="admin-quiz-ai@example.com", password_hash="x", role=UserRole.ADMIN)
            self.member = User(name="Member", email="member-quiz-ai@example.com", password_hash="x")
            self.user = User(name="User", email="user-quiz-ai@example.com", password_hash="x")
            category = Category(name="Learning", slug="quiz-ai-learning")
            session.add_all([self.admin, self.member, self.user, category])
            session.flush()
            session.add(Membership(user_id=self.member.id, status=MembershipStatus.ACTIVE, expires_at=now + timedelta(days=30)))
            book = Book(category_id=category.id, title="Grounded Course", slug="grounded-course", language="en", book_type=BookType.EDUCATIONAL, status=BookStatus.PUBLISHED, created_by=self.admin.id)
            session.add(book)
            session.flush()
            edition = Edition(book_id=book.id, page_count=2)
            session.add(edition)
            session.flush()
            file = DigitalFile(edition_id=edition.id, file_url="/content", storage_key="books/quiz.pdf", file_type="PDF", access_level="PUBLIC", processing_status=ProcessingStatus.READY, uploaded_by=self.admin.id)
            session.add(file)
            session.flush()
            chapter = Chapter(edition_id=edition.id, chapter_number=1, title="Grounded Concepts", page_start=1, page_end=2)
            session.add(chapter)
            source = "Grounded learning explains observation, evidence, comparison, and careful application. " * 8
            session.add_all([
                DocumentPage(digital_file_id=file.id, page_number=1, content=source),
                DocumentPage(digital_file_id=file.id, page_number=2, content=source),
            ])
            session.commit()
            self.chapter_id = str(chapter.id)
            self.book_id = book.id
            self.page_ids = list(session.scalars(select(DocumentPage.id)).all())

    @staticmethod
    def headers(user: User) -> dict[str, str]:
        token, _ = create_access_token(user.id)
        return {"Authorization": f"Bearer {token}"}

    @property
    def path(self) -> str:
        return f"/api/v1/admin/chapters/{self.chapter_id}/quiz/generate"

    def generate(self, provider: FakeQuizProvider | None = None):
        provider = provider or FakeQuizProvider()
        with patch("app.ai.services.quiz_generation_service.get_provider", return_value=provider):
            response = self.client.post(self.path, headers=self.headers(self.admin), json={"difficulty": "MEDIUM", "question_count": 3})
        return response, provider

    def test_authorization_source_and_learning_eligibility(self) -> None:
        self.assertEqual(self.client.post(self.path, headers=self.headers(self.user), json={}).status_code, 403)
        self.assertEqual(self.client.post(self.path, headers=self.headers(self.member), json={}).status_code, 403)
        self.assertEqual(self.client.post(f"/api/v1/admin/chapters/{uuid.uuid4()}/quiz/generate", headers=self.headers(self.admin), json={}).status_code, 404)
        self.assertEqual(self.client.post(self.path, headers=self.headers(self.admin), json={"question_count": 21}).status_code, 422)

        with Session(engine) as session:
            for page_id in self.page_ids:
                session.get(DocumentPage, page_id).content = ""
            session.commit()
        response, provider = self.generate()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(provider.calls, [])

        with Session(engine) as session:
            session.get(Book, self.book_id).book_type = BookType.FICTION
            session.commit()
        response, provider = self.generate()
        self.assertEqual(response.status_code, 422)
        self.assertEqual(provider.calls, [])

    def test_invalid_ai_output_is_rejected_without_partial_records(self) -> None:
        invalid = ["not json", quiz_json(correct=0), quiz_json(correct=2), quiz_json(duplicate_options=True)]
        for content in invalid:
            with self.subTest(content=content[:20]):
                response, _ = self.generate(FakeQuizProvider(content))
                self.assertEqual(response.status_code, 502, response.text)
                with Session(engine) as session:
                    self.assertEqual(session.scalar(select(func.count()).select_from(Quiz)), 0)
                    self.assertEqual(session.scalar(select(func.count()).select_from(QuizQuestion)), 0)
                    self.assertEqual(session.scalar(select(func.count()).select_from(QuizOption)), 0)

        response, _ = self.generate(FakeQuizProvider(fail=True))
        self.assertEqual(response.status_code, 503)
        with Session(engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Quiz)), 0)

    def test_valid_draft_uses_existing_editor_publish_and_quiz_engine(self) -> None:
        generated, provider = self.generate()
        self.assertEqual(generated.status_code, 200, generated.text)
        quiz = generated.json()
        self.assertEqual(quiz["generated_by"], "AI")
        self.assertEqual(quiz["ai_model"], provider.model)
        self.assertFalse(quiz["is_published"])
        self.assertEqual(len(quiz["questions"]), 3)
        self.assertTrue(all(sum(option["is_correct"] for option in question["options"]) == 1 for question in quiz["questions"]))
        self.assertIn("different parts", provider.calls[0][1])
        self.assertNotIn("is_correct", self.client.get(f"/api/v1/quizzes/{quiz['id']}", headers=self.headers(self.member)).text)

        with patch("app.ai.services.quiz_generation_service.get_provider", return_value=provider):
            duplicate = self.client.post(self.path, headers=self.headers(self.admin), json={"difficulty": "HARD", "question_count": 3})
        self.assertEqual(duplicate.json()["id"], quiz["id"])
        self.assertEqual(len(provider.calls), 1)

        edited = self.client.patch(f"/api/v1/admin/quizzes/{quiz['id']}", headers=self.headers(self.admin), json={"title": "Reviewed AI Quiz"})
        self.assertEqual(edited.json()["title"], "Reviewed AI Quiz")
        published = self.client.patch(f"/api/v1/admin/quizzes/{quiz['id']}", headers=self.headers(self.admin), json={"is_published": True})
        self.assertTrue(published.json()["is_published"])
        student = self.client.get(f"/api/v1/quizzes/{quiz['id']}", headers=self.headers(self.member))
        self.assertEqual(student.status_code, 200, student.text)
        self.assertNotIn("is_correct", student.text)
        self.assertNotIn("explanation", student.text)

        started = self.client.post(f"/api/v1/quizzes/{quiz['id']}/attempts", headers=self.headers(self.member)).json()
        for question in quiz["questions"]:
            correct = next(option for option in question["options"] if option["is_correct"])
            saved = self.client.put(f"/api/v1/quiz-attempts/{started['id']}/answers/{question['id']}", headers=self.headers(self.member), json={"selected_option_id": correct["id"]})
            self.assertEqual(saved.status_code, 200, saved.text)
        result = self.client.post(f"/api/v1/quiz-attempts/{started['id']}/submit", headers=self.headers(self.member))
        self.assertEqual(result.json()["score"], 100)
        self.assertIn("explanation", result.text)

    def test_regeneration_preserves_attempt_history(self) -> None:
        generated, _ = self.generate()
        quiz = generated.json()
        same_provider = FakeQuizProvider()
        with patch("app.ai.services.quiz_generation_service.get_provider", return_value=same_provider):
            regenerated = self.client.post(f"/api/v1/admin/quizzes/{quiz['id']}/regenerate", headers=self.headers(self.admin), json={})
        self.assertEqual(regenerated.status_code, 200, regenerated.text)
        self.assertEqual(regenerated.json()["id"], quiz["id"])

        self.client.patch(f"/api/v1/admin/quizzes/{quiz['id']}", headers=self.headers(self.admin), json={"is_published": True})
        started = self.client.post(f"/api/v1/quizzes/{quiz['id']}/attempts", headers=self.headers(self.member)).json()
        with Session(engine) as session:
            attempt = session.get(QuizAttempt, uuid.UUID(started["id"]))
            attempt.completed_at = datetime.now(timezone.utc)
            session.commit()
        self.client.patch(f"/api/v1/admin/quizzes/{quiz['id']}", headers=self.headers(self.admin), json={"is_published": False})

        new_provider = FakeQuizProvider()
        with patch("app.ai.services.quiz_generation_service.get_provider", return_value=new_provider):
            replacement = self.client.post(f"/api/v1/admin/quizzes/{quiz['id']}/regenerate", headers=self.headers(self.admin), json={})
        self.assertEqual(replacement.status_code, 200, replacement.text)
        self.assertNotEqual(replacement.json()["id"], quiz["id"])
        with Session(engine) as session:
            self.assertIsNotNone(session.get(QuizAttempt, uuid.UUID(started["id"])))
            self.assertEqual(session.scalar(select(func.count()).select_from(Quiz)), 2)

    def test_large_source_sampling_is_bounded_and_distributed(self) -> None:
        source = "BEGIN " + "x" * (MAX_QUIZ_SOURCE_CHARS * 2) + " END"
        selected = _representative_source(source)
        self.assertLessEqual(len(selected), MAX_QUIZ_SOURCE_CHARS + 100)
        self.assertIn("BEGIN", selected)
        self.assertIn("END", selected)
        self.assertGreaterEqual(selected.count("[SECTION BREAK]"), 4)


if __name__ == "__main__":
    unittest.main()
