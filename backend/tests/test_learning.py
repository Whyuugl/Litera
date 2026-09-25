import os
import unittest
from datetime import datetime, timedelta, timezone

os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-characters"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_session
from app.core.security import create_access_token
from app.main import app
from app.models import (
    Book,
    BookStatus,
    BookType,
    Category,
    Chapter,
    Edition,
    Membership,
    MembershipStatus,
    User,
    UserRole,
)


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


def test_session():
    with Session(engine, expire_on_commit=False) as session:
        yield session


class LearningApiTest(unittest.TestCase):
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
        with Session(engine, expire_on_commit=False) as session:
            self.admin = User(name="Admin", email="quiz-admin@example.com", password_hash="x", role=UserRole.ADMIN)
            self.member = User(name="Member", email="quiz-member@example.com", password_hash="x")
            self.other = User(name="Other", email="quiz-other@example.com", password_hash="x")
            self.user = User(name="User", email="quiz-user@example.com", password_hash="x")
            category = Category(name="Education", slug="education")
            session.add_all([self.admin, self.member, self.other, self.user, category])
            session.flush()
            expires = datetime.now(timezone.utc) + timedelta(days=30)
            session.add_all([
                Membership(user_id=self.member.id, status=MembershipStatus.ACTIVE, expires_at=expires),
                Membership(user_id=self.other.id, status=MembershipStatus.ACTIVE, expires_at=expires),
            ])
            book = Book(
                category_id=category.id,
                title="Learning Test",
                slug="learning-test",
                language="en",
                book_type=BookType.EDUCATIONAL,
                status=BookStatus.PUBLISHED,
                created_by=self.admin.id,
            )
            session.add(book)
            session.flush()
            edition = Edition(book_id=book.id, page_count=10)
            session.add(edition)
            session.flush()
            chapter = Chapter(edition_id=edition.id, chapter_number=1, title="Foundations", page_start=1, page_end=10)
            session.add(chapter)
            session.commit()
            self.edition_id = str(edition.id)
            self.chapter_id = str(chapter.id)

    @staticmethod
    def headers(user: User) -> dict[str, str]:
        token, _ = create_access_token(user.id)
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def payload(published: bool = False) -> dict:
        return {
            "title": "Chapter Review",
            "difficulty": "MEDIUM",
            "is_published": published,
            "questions": [
                {
                    "question": "What is the first answer?",
                    "explanation": "The first option is correct.",
                    "options": [
                        {"option_text": "First", "is_correct": True},
                        {"option_text": "Second", "is_correct": False},
                    ],
                },
                {
                    "question": "What is the second answer?",
                    "explanation": "The second option is correct.",
                    "options": [
                        {"option_text": "First", "is_correct": False},
                        {"option_text": "Second", "is_correct": True},
                    ],
                },
            ],
        }

    def create_quiz(self, published: bool = False) -> dict:
        response = self.client.post(
            f"/api/v1/admin/chapters/{self.chapter_id}/quizzes",
            headers=self.headers(self.admin),
            json=self.payload(published),
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_admin_authorization_validation_and_transaction(self) -> None:
        denied = self.client.post(
            f"/api/v1/admin/chapters/{self.chapter_id}/quizzes",
            headers=self.headers(self.user),
            json=self.payload(),
        )
        self.assertEqual(denied.status_code, 403)
        invalid = self.payload()
        invalid["questions"][0]["options"][1]["is_correct"] = True
        response = self.client.post(
            f"/api/v1/admin/chapters/{self.chapter_id}/quizzes",
            headers=self.headers(self.admin),
            json=invalid,
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            self.client.get(
                f"/api/v1/admin/chapters/{self.chapter_id}/quizzes", headers=self.headers(self.admin)
            ).json(),
            [],
        )
        invalid = self.payload()
        invalid["questions"][0]["options"] = invalid["questions"][0]["options"][:1]
        self.assertEqual(
            self.client.post(
                f"/api/v1/admin/chapters/{self.chapter_id}/quizzes",
                headers=self.headers(self.admin), json=invalid,
            ).status_code,
            422,
        )

    def test_publish_access_attempt_grading_retake_and_history_safety(self) -> None:
        quiz = self.create_quiz()
        quiz_id = quiz["id"]
        self.assertEqual(
            self.client.get(f"/api/v1/chapters/{self.chapter_id}/quizzes", headers=self.headers(self.member)).json(),
            [],
        )
        self.client.patch(
            f"/api/v1/admin/quizzes/{quiz_id}", headers=self.headers(self.admin), json={"is_published": True}
        )
        self.assertEqual(
            self.client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=self.headers(self.user)).status_code,
            403,
        )
        safe = self.client.get(f"/api/v1/quizzes/{quiz_id}", headers=self.headers(self.member))
        self.assertEqual(safe.status_code, 200)
        self.assertNotIn("is_correct", safe.text)
        self.assertNotIn("explanation", safe.text)

        started = self.client.post(
            f"/api/v1/quizzes/{quiz_id}/attempts", headers=self.headers(self.member)
        )
        self.assertEqual(started.status_code, 201, started.text)
        attempt_id = started.json()["id"]
        questions = started.json()["quiz"]["questions"]
        first, second = questions
        self.assertNotIn("is_correct", started.text)

        answer_url = f"/api/v1/quiz-attempts/{attempt_id}/answers/{first['id']}"
        self.client.put(answer_url, headers=self.headers(self.member), json={"selected_option_id": first["options"][1]["id"]})
        changed = self.client.put(answer_url, headers=self.headers(self.member), json={"selected_option_id": first["options"][0]["id"]})
        self.assertEqual(changed.status_code, 200)
        self.assertNotIn("correct", changed.text)
        self.assertEqual(
            self.client.put(answer_url, headers=self.headers(self.other), json={"selected_option_id": first["options"][0]["id"]}).status_code,
            404,
        )
        self.client.put(
            f"/api/v1/quiz-attempts/{attempt_id}/answers/{second['id']}",
            headers=self.headers(self.member),
            json={"selected_option_id": second["options"][0]["id"]},
        )
        result = self.client.post(
            f"/api/v1/quiz-attempts/{attempt_id}/submit",
            headers=self.headers(self.member),
            json={"score": 100},
        )
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["score"], 50)
        self.assertEqual(result.json()["correct_answers"], 1)
        self.assertIn("correct_answer", result.text)
        self.assertIn("explanation", result.text)
        self.assertEqual(
            self.client.put(answer_url, headers=self.headers(self.member), json={"selected_option_id": first["options"][1]["id"]}).status_code,
            409,
        )

        retake = self.client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=self.headers(self.member)).json()
        self.assertNotEqual(retake["id"], attempt_id)
        history = self.client.get(
            f"/api/v1/quizzes/{quiz_id}/attempts/me", headers=self.headers(self.member)
        ).json()
        self.assertEqual(len(history), 2)
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/quizzes/{quiz_id}", headers=self.headers(self.admin)).status_code,
            409,
        )
        structural = self.payload()["questions"]
        self.assertEqual(
            self.client.patch(
                f"/api/v1/admin/quizzes/{quiz_id}", headers=self.headers(self.admin), json={"questions": structural}
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/admin/quizzes/{quiz_id}", headers=self.headers(self.admin), json={"is_published": False}
            ).status_code,
            200,
        )

    def test_unanswered_submission_and_learning_progress(self) -> None:
        quiz = self.create_quiz(True)
        started = self.client.post(
            f"/api/v1/quizzes/{quiz['id']}/attempts", headers=self.headers(self.member)
        ).json()
        self.assertEqual(
            self.client.post(
                f"/api/v1/quiz-attempts/{started['id']}/submit", headers=self.headers(self.member)
            ).status_code,
            409,
        )
        progress = self.client.get(
            f"/api/v1/learning/editions/{self.edition_id}/progress", headers=self.headers(self.member)
        )
        self.assertEqual(progress.status_code, 200, progress.text)
        self.assertEqual(progress.json()["quizzes_available"], 1)
        self.assertEqual(progress.json()["quizzes_completed"], 0)
