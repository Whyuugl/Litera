import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-characters"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.ai.providers.base import AIProviderError, GeneratedText, LLMProvider
from app.ai.services.summary_service import MAX_SOURCE_CHARS, _chunks
from app.core.database import Base, get_session
from app.core.security import create_access_token
from app.main import app
from app.models import (
    AISummary,
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
    SummaryStatus,
    User,
    UserRole,
)


engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)


def test_session():
    with Session(engine, expire_on_commit=False) as session:
        yield session


class FakeProvider(LLMProvider):
    name = "fake"
    model = "fake-summary-1"

    def __init__(self, fail: bool = False):
        self.calls: list[tuple[str, str]] = []
        self.fail = fail

    async def generate(self, system: str, prompt: str) -> GeneratedText:
        self.calls.append((system, prompt))
        if self.fail:
            raise AIProviderError("provider unavailable")
        return GeneratedText(
            "Overview\nGrounded overview.\n\nKey ideas\nOne idea.\n\n"
            "Important concepts\nOne concept.\n\nWhat to remember\nRemember this."
        )


class SummaryApiTest(unittest.TestCase):
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
            self.admin = User(
                name="Admin", email="admin-ai@example.com", password_hash="x", role=UserRole.ADMIN
            )
            self.member = User(name="Member", email="member-ai@example.com", password_hash="x")
            self.user = User(name="User", email="user-ai@example.com", password_hash="x")
            category = Category(name="Learning", slug="ai-learning")
            session.add_all([self.admin, self.member, self.user, category])
            session.flush()
            session.add(
                Membership(
                    user_id=self.member.id,
                    status=MembershipStatus.ACTIVE,
                    expires_at=now + timedelta(days=30),
                )
            )
            book = Book(
                category_id=category.id,
                title="Grounded Reading",
                slug="grounded-reading",
                language="en",
                book_type=BookType.EDUCATIONAL,
                status=BookStatus.PUBLISHED,
                created_by=self.admin.id,
            )
            session.add(book)
            session.flush()
            edition = Edition(book_id=book.id, page_count=2)
            session.add(edition)
            session.flush()
            digital = DigitalFile(
                edition_id=edition.id,
                file_url="/content",
                storage_key="books/test.pdf",
                file_type="PDF",
                access_level="PUBLIC",
                processing_status=ProcessingStatus.READY,
                uploaded_by=self.admin.id,
            )
            session.add(digital)
            session.flush()
            chapter = Chapter(
                edition_id=edition.id,
                chapter_number=1,
                title="Foundations",
                page_start=1,
                page_end=2,
            )
            session.add_all(
                [
                    chapter,
                    DocumentPage(
                        digital_file_id=digital.id,
                        page_number=1,
                        content="A grounded first page about careful reading.",
                    ),
                    DocumentPage(
                        digital_file_id=digital.id,
                        page_number=2,
                        content="A second page containing an important concept.",
                    ),
                ]
            )
            session.commit()
            self.chapter_id = str(chapter.id)
            self.edition_id = str(edition.id)
            self.book_id = book.id
            self.page_id = session.scalar(
                select(DocumentPage.id).where(DocumentPage.page_number == 2)
            )

    @staticmethod
    def headers(user: User) -> dict[str, str]:
        token, _ = create_access_token(user.id)
        return {"Authorization": f"Bearer {token}"}

    def test_authorization_cache_hash_and_invalidation(self) -> None:
        provider = FakeProvider()
        path = f"/api/v1/admin/chapters/{self.chapter_id}/summary/generate"
        self.assertEqual(self.client.post(path, headers=self.headers(self.user)).status_code, 403)

        with patch("app.ai.services.summary_service.get_provider", return_value=provider):
            generated = self.client.post(path, headers=self.headers(self.admin))
            self.assertEqual(generated.status_code, 200, generated.text)
            first = generated.json()
            self.assertEqual(first["status"], "READY")
            self.assertEqual(len(first["source_content_hash"]), 64)
            calls = len(provider.calls)
            cached = self.client.post(path, headers=self.headers(self.admin))
            self.assertEqual(cached.json()["id"], first["id"])
            self.assertEqual(len(provider.calls), calls)

            member_path = f"/api/v1/chapters/{self.chapter_id}/summary"
            self.assertEqual(self.client.get(member_path, headers=self.headers(self.user)).status_code, 403)
            self.assertEqual(self.client.get(member_path, headers=self.headers(self.member)).status_code, 200)
            self.assertEqual(len(provider.calls), calls)

            with Session(engine) as session:
                session.get(DocumentPage, self.page_id).content = "Changed source content."
                session.commit()
            stale = self.client.get(
                f"/api/v1/admin/chapters/{self.chapter_id}/summary",
                headers=self.headers(self.admin),
            )
            self.assertTrue(stale.json()["is_stale"])
            self.assertEqual(self.client.get(member_path, headers=self.headers(self.member)).status_code, 404)
            regenerated = self.client.post(path, headers=self.headers(self.admin))
            self.assertEqual(regenerated.status_code, 200, regenerated.text)
            self.assertNotEqual(regenerated.json()["source_content_hash"], first["source_content_hash"])
            self.assertGreater(len(provider.calls), calls)

    def test_missing_source_duplicate_and_provider_failure_are_isolated(self) -> None:
        provider = FakeProvider()
        with Session(engine, expire_on_commit=False) as session:
            empty = Chapter(
                edition_id=uuid.UUID(self.edition_id),
                chapter_number=2,
                title="Empty",
                page_start=3,
                page_end=3,
            )
            session.add(empty)
            session.commit()
            empty_id = str(empty.id)
        with patch("app.ai.services.summary_service.get_provider", return_value=provider):
            missing = self.client.post(
                f"/api/v1/admin/chapters/{empty_id}/summary/generate",
                headers=self.headers(self.admin),
            )
            self.assertEqual(missing.status_code, 422)
            self.assertEqual(provider.calls, [])

        working = FakeProvider()
        path = f"/api/v1/admin/chapters/{self.chapter_id}/summary/generate"
        with patch("app.ai.services.summary_service.get_provider", return_value=working):
            self.assertEqual(self.client.post(path, headers=self.headers(self.admin)).status_code, 200)
        with Session(engine) as session:
            summary = session.scalar(select(AISummary))
            summary.status = SummaryStatus.PENDING
            session.commit()
        with patch("app.ai.services.summary_service.get_provider", return_value=working):
            self.assertEqual(self.client.post(path, headers=self.headers(self.admin)).status_code, 409)

        with Session(engine) as session:
            summary = session.scalar(select(AISummary))
            summary.status = SummaryStatus.READY
            session.commit()
        failing = FakeProvider(fail=True)
        with patch("app.ai.services.summary_service.get_provider", return_value=failing):
            failed = self.client.post(
                f"{path}?regenerate=true", headers=self.headers(self.admin)
            )
            self.assertEqual(failed.status_code, 503)
        with Session(engine) as session:
            self.assertEqual(session.scalar(select(AISummary)).status, SummaryStatus.FAILED)
        self.assertEqual(self.client.get("/api/v1/books").status_code, 200)
        self.assertEqual(
            self.client.get(f"/api/v1/editions/{self.edition_id}/reader").status_code,
            200,
        )

    def test_book_summary_is_hierarchical_and_fiction_is_spoiler_free(self) -> None:
        bounded = _chunks("x" * (MAX_SOURCE_CHARS * 2 + 17))
        self.assertEqual("".join(bounded), "x" * (MAX_SOURCE_CHARS * 2 + 17))
        self.assertLessEqual(max(map(len, bounded)), MAX_SOURCE_CHARS)
        with Session(engine) as session:
            session.add(
                Chapter(
                    edition_id=uuid.UUID(self.edition_id),
                    chapter_number=2,
                    title="Practice",
                    page_start=2,
                    page_end=2,
                )
            )
            session.commit()
        provider = FakeProvider()
        with patch("app.ai.services.summary_service.get_provider", return_value=provider):
            generated = self.client.post(
                f"/api/v1/admin/editions/{self.edition_id}/summary/generate",
                headers=self.headers(self.admin),
            )
        self.assertEqual(generated.status_code, 200, generated.text)
        self.assertEqual(generated.json()["summary_type"], "BOOK")
        self.assertGreater(len(provider.calls), 2)

        with Session(engine) as session:
            session.get(Book, self.book_id).book_type = BookType.FICTION
            session.commit()
        fiction_provider = FakeProvider()
        with patch(
            "app.ai.services.summary_service.get_provider", return_value=fiction_provider
        ):
            fiction = self.client.post(
                f"/api/v1/admin/chapters/{self.chapter_id}/summary/generate",
                headers=self.headers(self.admin),
            )
        self.assertEqual(fiction.status_code, 200, fiction.text)
        self.assertEqual(fiction.json()["spoiler_mode"], "SPOILER_FREE")
        self.assertIn("Avoid revealing endings", fiction_provider.calls[0][1])
