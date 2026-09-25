import io
import os
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-characters"

from fastapi import UploadFile
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_session
from app.core.security import create_access_token
from app.main import app
from app.models import AccessLevel, Book, BookStatus, BookType, Category, DigitalFile, Edition, Membership, MembershipStatus, ProcessingStatus, User, UserRole
from app.services import digital
from app.services.storage import LocalStorage


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


def test_session():
    with Session(engine, expire_on_commit=False) as session:
        yield session


def pdf_bytes(pages: int = 3) -> bytes:
    stream = io.BytesIO()
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    writer.write(stream)
    return stream.getvalue()


class DigitalReaderApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        app.dependency_overrides[get_session] = test_session
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls.temp = tempfile.TemporaryDirectory()
        cls.original_storage = digital.storage
        digital.storage = LocalStorage(Path(cls.temp.name))

    @classmethod
    def tearDownClass(cls) -> None:
        digital.storage = cls.original_storage
        app.dependency_overrides.clear()
        cls.client.__exit__(None, None, None)
        cls.temp.cleanup()
        engine.dispose()

    def setUp(self) -> None:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        with Session(engine, expire_on_commit=False) as session:
            self.admin = User(name="Admin", email="admin-reader@example.com", password_hash="unused", role=UserRole.ADMIN)
            self.user = User(name="Reader", email="reader@example.com", password_hash="unused", role=UserRole.USER)
            self.other = User(name="Other", email="other-reader@example.com", password_hash="unused", role=UserRole.USER)
            category = Category(name="Learning", slug="learning")
            session.add_all([self.admin, self.user, self.other, category])
            session.flush()
            book = Book(
                category_id=category.id,
                title="Reader Test",
                slug="reader-test",
                language="en",
                book_type=BookType.EDUCATIONAL,
                status=BookStatus.PUBLISHED,
                created_by=self.admin.id,
            )
            session.add(book)
            session.flush()
            edition = Edition(book_id=book.id, publisher="Litera", page_count=3)
            session.add(edition)
            session.commit()
            self.edition_id = str(edition.id)

    @staticmethod
    def headers(user: User) -> dict[str, str]:
        token, _ = create_access_token(user.id)
        return {"Authorization": f"Bearer {token}"}

    def test_pdf_reader_progress_bookmarks_and_safety(self) -> None:
        denied = self.client.post(
            f"/api/v1/admin/editions/{self.edition_id}/digital-files",
            headers=self.headers(self.user),
            files={"file": ("book.pdf", pdf_bytes(), "application/pdf")},
        )
        self.assertEqual(denied.status_code, 403)

        uploaded = self.client.post(
            f"/api/v1/admin/editions/{self.edition_id}/digital-files",
            headers=self.headers(self.admin),
            files={"file": ("book.pdf", pdf_bytes(), "application/pdf")},
            data={"access_level": "PUBLIC", "allow_download": "false"},
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        file_id = uploaded.json()["id"]
        self.assertEqual(uploaded.json()["processing_status"], "READY")
        self.assertFalse(uploaded.json()["allow_download"])
        self.assertNotIn(self.temp.name, uploaded.text)
        with Session(engine) as session:
            stored = session.get(DigitalFile, uuid.UUID(file_id))
            self.assertTrue(stored.storage_key.startswith(f"books/{self.edition_id}/"))
            self.assertNotIn("book.pdf", stored.storage_key)

        metadata = self.client.get(f"/api/v1/editions/{self.edition_id}/reader")
        self.assertEqual(metadata.status_code, 200, metadata.text)
        self.assertEqual(metadata.json()["page_count"], 3)
        self.assertEqual(metadata.json()["chapters"][0]["title"], "Full Document")
        pages = self.client.get(f"/api/v1/editions/{self.edition_id}/pages")
        self.assertEqual(pages.status_code, 200, pages.text)
        self.assertEqual([item["page_number"] for item in pages.json()], [1, 2, 3])

        content = self.client.get(
            f"/api/v1/digital-files/{file_id}/content",
            headers={"Range": "bytes=0-9"},
        )
        self.assertEqual(content.status_code, 206)
        self.assertEqual(content.content, pdf_bytes()[:10])
        self.assertEqual(content.headers["accept-ranges"], "bytes")
        self.assertIn("inline", content.headers["content-disposition"])
        self.assertEqual(self.client.get(f"/api/v1/digital-files/{file_id}/content?download=true").status_code, 403)

        self.client.patch(
            f"/api/v1/admin/digital-files/{file_id}", headers=self.headers(self.admin), json={"access_level": "REGISTERED"}
        )
        self.assertEqual(self.client.get(f"/api/v1/digital-files/{file_id}/content").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/editions/{self.edition_id}/pages").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/digital-files/{file_id}/content", headers=self.headers(self.user)).status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/editions/{self.edition_id}/pages", headers=self.headers(self.user)).status_code, 200)
        self.client.patch(
            f"/api/v1/admin/digital-files/{file_id}", headers=self.headers(self.admin), json={"access_level": "MEMBER"}
        )
        self.assertEqual(self.client.get(f"/api/v1/digital-files/{file_id}/content", headers=self.headers(self.user)).status_code, 403)
        with Session(engine) as session:
            session.add(Membership(user_id=self.user.id, status=MembershipStatus.ACTIVE, expires_at=datetime.now(timezone.utc) + timedelta(days=1)))
            session.commit()
        self.assertEqual(self.client.get(f"/api/v1/digital-files/{file_id}/content", headers=self.headers(self.user)).status_code, 200)
        with Session(engine) as session:
            membership = session.query(Membership).filter_by(user_id=self.user.id).one()
            membership.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
            session.commit()
        self.assertEqual(self.client.get(f"/api/v1/digital-files/{file_id}/content", headers=self.headers(self.user)).status_code, 403)
        self.client.patch(
            f"/api/v1/admin/digital-files/{file_id}", headers=self.headers(self.admin), json={"access_level": "PUBLIC"}
        )

        progress = self.client.put(
            f"/api/v1/reading-progress/{self.edition_id}",
            headers=self.headers(self.user),
            json={"current_page": 2, "position_data": {"offset": 0.42}},
        )
        self.assertEqual(progress.status_code, 200, progress.text)
        self.assertAlmostEqual(progress.json()["progress_percentage"], 66.67)
        self.assertEqual(progress.json()["position_data"], {"offset": 0.42})
        self.assertEqual(
            self.client.put(
                f"/api/v1/reading-progress/{self.edition_id}",
                headers=self.headers(self.user), json={"current_page": 99},
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.get("/api/v1/reading-progress", headers=self.headers(self.user)).json()[0]["book"]["title"],
            "Reader Test",
        )
        self.assertIsNone(
            self.client.get(
                f"/api/v1/reading-progress/{self.edition_id}", headers=self.headers(self.other)
            ).json()
        )

        bookmark = self.client.post(
            "/api/v1/bookmarks",
            headers=self.headers(self.user),
            json={"edition_id": self.edition_id, "page_number": 2, "position_data": {"offset": 0.6}, "note": "Review"},
        )
        self.assertEqual(bookmark.status_code, 201, bookmark.text)
        self.assertEqual(bookmark.json()["position_data"], {"offset": 0.6})
        bookmark_id = bookmark.json()["id"]
        edited = self.client.patch(
            f"/api/v1/bookmarks/{bookmark_id}", headers=self.headers(self.user), json={"note": "Keep"}
        )
        self.assertEqual(edited.json()["note"], "Keep")
        self.assertEqual(
            len(self.client.get(f"/api/v1/bookmarks?edition_id={self.edition_id}", headers=self.headers(self.user)).json()),
            1,
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/bookmarks/{bookmark_id}", headers=self.headers(self.other)).status_code,
            404,
        )

        replacement = self.client.post(
            f"/api/v1/admin/digital-files/{file_id}/replace",
            headers=self.headers(self.admin),
            files={"file": ("replacement.pdf", pdf_bytes(1), "application/pdf")},
        )
        self.assertEqual(replacement.status_code, 409)
        self.assertEqual(
            self.client.delete(f"/api/v1/admin/digital-files/{file_id}", headers=self.headers(self.admin)).status_code,
            409,
        )

        with Session(engine) as session:
            stored = session.get(DigitalFile, uuid.UUID(file_id))
            stored.processing_status = ProcessingStatus.FAILED
            session.commit()
        self.assertEqual(self.client.get(f"/api/v1/editions/{self.edition_id}/reader").status_code, 404)

    def test_rejects_non_pdf(self) -> None:
        response = self.client.post(
            f"/api/v1/admin/editions/{self.edition_id}/digital-files",
            headers=self.headers(self.admin),
            files={"file": ("book.pdf", b"not a pdf", "application/pdf")},
        )
        self.assertEqual(response.status_code, 400)

    def test_size_limit_and_database_failure_cleanup(self) -> None:
        original_limit = digital.max_book_file_size
        digital.max_book_file_size = lambda: 5
        try:
            oversized = self.client.post(
                f"/api/v1/admin/editions/{self.edition_id}/digital-files",
                headers=self.headers(self.admin),
                files={"file": ("large.pdf", b"%PDF-too-large", "application/pdf")},
            )
            self.assertEqual(oversized.status_code, 400)
        finally:
            digital.max_book_file_size = original_limit

        before = set(Path(self.temp.name).rglob("*.pdf"))
        with Session(engine, expire_on_commit=False) as session:
            edition = session.get(Edition, uuid.UUID(self.edition_id))
            admin = session.get(User, self.admin.id)

            def fail_commit(_session):
                raise RuntimeError("database unavailable")

            event.listen(session, "before_commit", fail_commit, once=True)
            upload = UploadFile(filename="orphan.pdf", file=io.BytesIO(pdf_bytes()), headers={"content-type": "application/pdf"})
            with self.assertRaises(RuntimeError):
                digital.upload_pdf(session, edition.id, upload, AccessLevel.PUBLIC, False, admin)
        self.assertEqual(set(Path(self.temp.name).rglob("*.pdf")), before)
