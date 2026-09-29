import asyncio
import os
import unittest
import uuid
from types import SimpleNamespace

os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-characters"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.ai.providers.base import EmbeddingProvider
from app.core.database import Base, get_session
from app.core.security import create_access_token
from app.main import app
from app.models import (
    AccessLevel, Book, BookChunk, BookStatus, BookType, Category, Chapter,
    DigitalFile, DigitalFileType, DocumentPage, Edition, ProcessingStatus,
    RAGStatus, User, UserRole,
)
from app.services import digital, rag


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


def test_session():
    with Session(engine, expire_on_commit=False) as session:
        yield session


class FakeEmbeddings(EmbeddingProvider):
    name = "fake"
    model = "fake-1536"
    dimensions = 1536

    def __init__(self, *, fail: bool = False, batch_size: int = 2):
        self.fail = fail
        self.settings = SimpleNamespace(batch_size=batch_size)
        self.batches: list[int] = []
        self.query_calls = 0

    @staticmethod
    def vector(text: str) -> list[float]:
        lowered = text.lower()
        values = [float(lowered.count("alpha") + 1), float(lowered.count("beta") + 1)]
        return values + [0.0] * 1534

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if self.fail:
            raise RuntimeError("provider down")
        self.batches.append(len(texts))
        return [self.vector(text) for text in texts]

    async def embed_text(self, text: str) -> list[float]:
        self.query_calls += 1
        return self.vector(text)


class RAGInfrastructureTest(unittest.TestCase):
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
            self.admin = User(name="Admin", email="rag-admin@example.com", password_hash="x", role=UserRole.ADMIN)
            self.user = User(name="User", email="rag-user@example.com", password_hash="x", role=UserRole.USER)
            category = Category(name="RAG", slug="rag")
            session.add_all([self.admin, self.user, category]); session.flush()
            for number, topic in enumerate(("alpha", "beta"), 1):
                book = Book(category_id=category.id, title=f"Book {topic}", slug=f"book-{topic}", language="en", book_type=BookType.EDUCATIONAL, status=BookStatus.PUBLISHED, created_by=self.admin.id)
                session.add(book); session.flush()
                edition = Edition(book_id=book.id, page_count=3)
                session.add(edition); session.flush()
                file = DigitalFile(
                    edition_id=edition.id, file_url="/file", storage_key=f"{topic}.pdf",
                    file_type=DigitalFileType.PDF, access_level=AccessLevel.PUBLIC,
                    processing_status=ProcessingStatus.READY, uploaded_by=self.admin.id,
                )
                session.add(file); session.flush()
                chapter = Chapter(edition_id=edition.id, chapter_number=1, title=f"{topic.title()} chapter", page_start=1, page_end=3)
                session.add(chapter); session.flush()
                session.add_all([
                    DocumentPage(digital_file_id=file.id, page_number=page, content=((topic + " concept. ") * 400).strip())
                    for page in range(1, 4)
                ])
                if number == 1:
                    self.file_id, self.edition_id, self.chapter_id = file.id, edition.id, chapter.id
                else:
                    self.other_file_id, self.other_edition_id = file.id, edition.id
            session.commit()
            self.admin_id, self.user_id = self.admin.id, self.user.id

    def headers(self, user_id: uuid.UUID) -> dict[str, str]:
        token, _ = create_access_token(user_id)
        return {"Authorization": f"Bearer {token}"}

    def test_chunking_preserves_chapter_pages_overlap_and_hash(self) -> None:
        chapter_a, chapter_b = uuid.uuid4(), uuid.uuid4()
        pages = [
            SimpleNamespace(page_number=1, content=("one sentence. " * 80)),
            SimpleNamespace(page_number=2, content=("two sentence. " * 80)),
            SimpleNamespace(page_number=3, content=("three sentence. " * 80)),
        ]
        chapters = [
            SimpleNamespace(id=chapter_a, page_start=1, page_end=2),
            SimpleNamespace(id=chapter_b, page_start=3, page_end=3),
        ]
        chunks = rag.chunk_pages(pages, chapters, target=100, overlap=20)
        self.assertGreater(len(chunks), 3)
        self.assertTrue(all(item.token_count <= 100 for item in chunks))
        self.assertFalse(any(item.chapter_id == chapter_a and item.page_end == 3 for item in chunks))
        self.assertTrue(all(item.page_start <= item.page_end for item in chunks))
        self.assertTrue(all(len(item.content_hash) == 64 for item in chunks))
        self.assertNotEqual(chunks[0].content_hash, chunks[1].content_hash)
        self.assertTrue(set(chunks[0].content.split()) & set(chunks[1].content.split()))

    def test_admin_only_and_ready_requirement(self) -> None:
        response = self.client.post(
            f"/api/v1/admin/digital-files/{self.file_id}/rag/index",
            headers=self.headers(self.user_id),
        )
        self.assertEqual(response.status_code, 403)
        with Session(engine, expire_on_commit=False) as session:
            file = session.get(DigitalFile, self.file_id)
            file.processing_status = ProcessingStatus.FAILED
            session.commit()
            with self.assertRaises(rag.RAGConflict):
                asyncio.run(rag.ingest(session, self.file_id, provider=FakeEmbeddings()))

            file.processing_status = ProcessingStatus.READY
            file.rag_status = RAGStatus.INDEXING
            session.commit()
            with self.assertRaises(rag.RAGConflict):
                asyncio.run(rag.ingest(session, self.file_id, provider=FakeEmbeddings()))

    def test_ingestion_batching_persistence_retrieval_scope_and_top_k(self) -> None:
        provider = FakeEmbeddings(batch_size=2)
        with Session(engine, expire_on_commit=False) as session:
            result = asyncio.run(rag.ingest(session, self.file_id, provider=provider))
            self.assertEqual(result["status"], RAGStatus.READY)
            self.assertGreater(result["chunk_count"], 1)
            self.assertTrue(all(size <= 2 for size in provider.batches))
            chunks = session.query(BookChunk).filter_by(digital_file_id=self.file_id).all()
            self.assertTrue(all(len(item.embedding) == 1536 for item in chunks))
            self.assertTrue(all(item.chapter_id == self.chapter_id for item in chunks))

            asyncio.run(rag.ingest(session, self.other_file_id, provider=FakeEmbeddings()))
            found = asyncio.run(rag.search(session, self.edition_id, "alpha", top_k=2, provider=provider))
            self.assertEqual(len(found), 2)
            self.assertEqual(provider.query_calls, 1)
            self.assertTrue(all("alpha" in item["content"] for item in found))
            self.assertTrue(all(item["chapter"]["title"] == "Alpha chapter" for item in found))
            self.assertTrue(all(item["page_start"] <= item["page_end"] for item in found))

    def test_failure_preserves_chunks_and_replacement_marks_stale(self) -> None:
        with Session(engine, expire_on_commit=False) as session:
            asyncio.run(rag.ingest(session, self.file_id, provider=FakeEmbeddings()))
            before = rag.repository.chunk_count(session, self.file_id)
            with self.assertRaises(rag.RAGUnavailable):
                asyncio.run(rag.ingest(session, self.file_id, force=True, provider=FakeEmbeddings(fail=True)))
            file = session.get(DigitalFile, self.file_id)
            self.assertEqual(file.rag_status, RAGStatus.FAILED)
            self.assertEqual(rag.repository.chunk_count(session, self.file_id), before)
            digital._replace_extracted(session, file, ["replacement text"], [(1, "New", 1, 1)])
            session.commit()
            self.assertEqual(file.rag_status, RAGStatus.STALE)

    def test_chapter_change_marks_index_stale(self) -> None:
        with Session(engine, expire_on_commit=False) as session:
            asyncio.run(rag.ingest(session, self.file_id, provider=FakeEmbeddings()))
            chapter = digital.update_chapter(
                session,
                self.chapter_id,
                digital.ChapterUpdate(title="Updated chapter"),
            )
            self.assertEqual(chapter.title, "Updated chapter")
            self.assertEqual(session.get(DigitalFile, self.file_id).rag_status, RAGStatus.STALE)

    def test_empty_source_and_dimension_mismatch_fail_cleanly(self) -> None:
        with Session(engine, expire_on_commit=False) as session:
            session.query(DocumentPage).filter_by(digital_file_id=self.file_id).update({"content": ""})
            session.commit()
            with self.assertRaises(rag.RAGUnavailable):
                asyncio.run(rag.ingest(session, self.file_id, provider=FakeEmbeddings()))
            self.assertEqual(session.get(DigitalFile, self.file_id).rag_status, RAGStatus.FAILED)

            wrong = FakeEmbeddings()
            wrong.dimensions = 3
            with self.assertRaises(rag.RAGUnavailable):
                asyncio.run(rag.ingest(session, self.other_file_id, provider=wrong))
            self.assertEqual(session.get(DigitalFile, self.other_file_id).rag_status, RAGStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
