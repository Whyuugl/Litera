import os
import unittest
import uuid

os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-characters"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_session
from app.core.security import create_access_token
from app.main import app
from app.models import User, UserRole


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def test_session():
    with Session(engine, expire_on_commit=False) as session:
        yield session


class CatalogApiTest(unittest.TestCase):
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
        self.admin = self.create_user("admin@example.com", UserRole.ADMIN)
        self.user = self.create_user("user@example.com", UserRole.USER)

    def create_user(self, email: str, role: UserRole) -> User:
        with Session(engine, expire_on_commit=False) as session:
            user = User(name=email.split("@")[0], email=email, password_hash="unused", role=role)
            session.add(user)
            session.commit()
            return user

    def headers(self, user: User) -> dict[str, str]:
        token, _ = create_access_token(user.id)
        return {"Authorization": f"Bearer {token}"}

    @property
    def admin_headers(self) -> dict[str, str]:
        return self.headers(self.admin)

    def create_category(self, name: str = "Programming") -> dict:
        response = self.client.post(
            "/api/v1/admin/categories",
            headers=self.admin_headers,
            json={"name": name},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def create_author(self, name: str = "Robert Martin") -> dict:
        response = self.client.post(
            "/api/v1/admin/authors",
            headers=self.admin_headers,
            json={"name": name},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def create_book(
        self,
        category_id: str,
        author_ids: list[str],
        *,
        title: str = "Clean Code",
        status: str = "PUBLISHED",
        book_type: str = "EDUCATIONAL",
        language: str = "en",
    ) -> dict:
        response = self.client.post(
            "/api/v1/admin/books",
            headers=self.admin_headers,
            json={
                "category_id": category_id,
                "author_ids": author_ids,
                "title": title,
                "description": "A software craftsmanship book",
                "language": language,
                "book_type": book_type,
                "status": status,
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_public_only_sees_published_books_and_detail_availability(self) -> None:
        category = self.create_category()
        author = self.create_author()
        published = self.create_book(category["id"], [author["id"]])
        self.create_book(category["id"], [author["id"]], title="Draft Book", status="DRAFT")
        self.create_book(
            category["id"], [author["id"]], title="Archived Book", status="ARCHIVED"
        )

        edition = self.client.post(
            f"/api/v1/admin/books/{published['id']}/editions",
            headers=self.admin_headers,
            json={"isbn": "9780132350884", "page_count": 464, "language": "en"},
        ).json()
        digital = self.client.post(
            f"/api/v1/admin/editions/{edition['id']}/digital-files",
            headers=self.admin_headers,
            json={
                "file_url": "s3://private-bucket/clean-code.pdf",
                "file_type": "PDF",
                "file_size": 1200,
                "access_level": "MEMBER",
            },
        )
        self.assertEqual(digital.status_code, 201)
        for barcode, copy_status in (("COPY-1", "AVAILABLE"), ("COPY-2", "BORROWED")):
            self.assertEqual(
                self.client.post(
                    f"/api/v1/admin/editions/{edition['id']}/copies",
                    headers=self.admin_headers,
                    json={"barcode": barcode, "status": copy_status},
                ).status_code,
                201,
            )

        listing = self.client.get("/api/v1/books").json()
        self.assertEqual(listing["total"], 1)
        self.assertEqual(listing["items"][0]["slug"], "clean-code")
        self.assertNotIn("created_by", listing["items"][0])

        detail = self.client.get("/api/v1/books/clean-code")
        self.assertEqual(detail.status_code, 200)
        body = detail.json()
        self.assertEqual(body["editions"][0]["digital"][0]["access_level"], "MEMBER")
        self.assertEqual(body["editions"][0]["physical"], {"total_copies": 2, "available_copies": 1})
        self.assertNotIn("file_url", detail.text)
        self.assertNotIn("COPY-1", detail.text)
        self.assertEqual(self.client.get(f"/api/v1/books/{published['id']}").status_code, 200)

    def test_search_filters_pagination_and_query_count(self) -> None:
        programming = self.create_category()
        fiction = self.create_category("Fiction")
        martin = self.create_author()
        doe = self.create_author("Jane Doe")
        self.create_book(programming["id"], [martin["id"]])
        self.create_book(
            fiction["id"],
            [doe["id"]],
            title="Moon Story",
            book_type="FICTION",
            language="id",
        )

        self.assertEqual(self.client.get("/api/v1/books?search=Martin").json()["total"], 1)
        self.assertEqual(
            self.client.get("/api/v1/books?category=fiction&book_type=FICTION&language=id").json()["total"],
            1,
        )
        page = self.client.get("/api/v1/books?page=1&page_size=1").json()
        self.assertEqual((page["total"], page["total_pages"], len(page["items"])), (2, 2, 1))

        statements = []
        listener = lambda *args: statements.append(args[2])
        event.listen(engine, "before_cursor_execute", listener)
        try:
            self.client.get("/api/v1/books")
        finally:
            event.remove(engine, "before_cursor_execute", listener)
        self.assertLessEqual(len(statements), 3)

    def test_user_cannot_manage_catalog(self) -> None:
        headers = self.headers(self.user)
        self.assertEqual(
            self.client.get("/api/v1/admin/books", headers=headers).status_code, 403
        )
        response = self.client.post(
            "/api/v1/admin/categories", headers=headers, json={"name": "Forbidden"}
        )
        self.assertEqual(response.status_code, 403)
        unknown = uuid.uuid4()
        self.assertEqual(
            self.client.get(
                f"/api/v1/admin/books/{unknown}", headers=headers
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/admin/books/{unknown}", headers=headers, json={"title": "No"}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.delete(
                f"/api/v1/admin/authors/{unknown}", headers=headers
            ).status_code,
            403,
        )

    def test_admin_reads_all_books_and_nested_resources(self) -> None:
        category = self.create_category()
        author = self.create_author()
        draft = self.create_book(
            category["id"], [author["id"]], title="Draft Guide", status="DRAFT"
        )
        published = self.create_book(category["id"], [author["id"]])
        edition = self.client.post(
            f"/api/v1/admin/books/{published['id']}/editions",
            headers=self.admin_headers,
            json={"publisher": "Litera Press"},
        ).json()
        self.client.post(
            f"/api/v1/admin/editions/{edition['id']}/digital-files",
            headers=self.admin_headers,
            json={
                "file_url": "https://example.com/clean-code.pdf",
                "file_type": "PDF",
                "access_level": "REGISTERED",
            },
        )
        self.client.post(
            f"/api/v1/admin/editions/{edition['id']}/copies",
            headers=self.admin_headers,
            json={"barcode": "ADMIN-READ-1"},
        )

        listing = self.client.get(
            "/api/v1/admin/books?status=DRAFT&search=Draft&page=1&page_size=10",
            headers=self.admin_headers,
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["items"][0]["id"], draft["id"])

        detail = self.client.get(
            f"/api/v1/admin/books/{published['id']}", headers=self.admin_headers
        )
        self.assertEqual(detail.status_code, 200)
        body = detail.json()
        self.assertEqual(body["editions"][0]["digital_files"][0]["file_type"], "PDF")
        self.assertEqual(body["editions"][0]["physical_copies"][0]["barcode"], "ADMIN-READ-1")
    def test_admin_creation_slug_collision_and_references(self) -> None:
        category = self.create_category()
        author = self.create_author()
        first = self.create_book(category["id"], [author["id"]])
        second = self.create_book(category["id"], [author["id"]], title="Clean Code")
        self.assertEqual(first["slug"], "clean-code")
        self.assertEqual(second["slug"], "clean-code-2")
        self.assertEqual(len(first["authors"]), 1)

        duplicate = self.client.post(
            "/api/v1/admin/categories",
            headers=self.admin_headers,
            json={"name": "Different", "slug": category["slug"]},
        )
        self.assertEqual(duplicate.status_code, 409)
        invalid_category = self.client.post(
            "/api/v1/admin/books",
            headers=self.admin_headers,
            json={
                "category_id": str(uuid.uuid4()),
                "author_ids": [author["id"]],
                "title": "Invalid",
                "language": "en",
                "book_type": "REFERENCE",
            },
        )
        self.assertEqual(invalid_category.status_code, 400)
        invalid_author = self.client.post(
            "/api/v1/admin/books",
            headers=self.admin_headers,
            json={
                "category_id": category["id"],
                "author_ids": [str(uuid.uuid4())],
                "title": "Invalid",
                "language": "en",
                "book_type": "REFERENCE",
            },
        )
        self.assertEqual(invalid_author.status_code, 400)

    def test_duplicate_isbn_barcode_and_safe_deletes(self) -> None:
        category = self.create_category()
        author = self.create_author()
        book = self.create_book(category["id"], [author["id"]])
        edition = self.client.post(
            f"/api/v1/admin/books/{book['id']}/editions",
            headers=self.admin_headers,
            json={"isbn": "ISBN-UNIQUE"},
        ).json()
        self.assertEqual(
            self.client.post(
                f"/api/v1/admin/books/{book['id']}/editions",
                headers=self.admin_headers,
                json={"isbn": "ISBN-UNIQUE"},
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/admin/editions/{edition['id']}/copies",
                headers=self.admin_headers,
                json={"barcode": "BARCODE-1"},
            ).status_code,
            201,
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/admin/editions/{edition['id']}/copies",
                headers=self.admin_headers,
                json={"barcode": "BARCODE-1"},
            ).status_code,
            409,
        )
        for path in (
            f"/api/v1/admin/categories/{category['id']}",
            f"/api/v1/admin/authors/{author['id']}",
            f"/api/v1/admin/books/{book['id']}",
            f"/api/v1/admin/editions/{edition['id']}",
        ):
            self.assertEqual(
                self.client.delete(path, headers=self.admin_headers).status_code, 409
            )

    def test_admin_updates_and_deletes_catalog_in_safe_order(self) -> None:
        category = self.create_category()
        author = self.create_author()
        book = self.create_book(category["id"], [author["id"]])
        edition = self.client.post(
            f"/api/v1/admin/books/{book['id']}/editions",
            headers=self.admin_headers,
            json={"publisher": "Old Publisher"},
        ).json()
        digital = self.client.post(
            f"/api/v1/admin/editions/{edition['id']}/digital-files",
            headers=self.admin_headers,
            json={
                "file_url": "https://example.com/book.pdf",
                "file_type": "PDF",
                "access_level": "REGISTERED",
            },
        ).json()
        copy = self.client.post(
            f"/api/v1/admin/editions/{edition['id']}/copies",
            headers=self.admin_headers,
            json={"barcode": "UPDATE-1"},
        ).json()

        patches = (
            (f"/api/v1/admin/categories/{category['id']}", {"description": "Updated"}),
            (f"/api/v1/admin/authors/{author['id']}", {"bio": "Updated"}),
            (f"/api/v1/admin/books/{book['id']}", {"title": "Updated Clean Code"}),
            (f"/api/v1/admin/editions/{edition['id']}", {"publisher": "New Publisher"}),
            (f"/api/v1/admin/digital-files/{digital['id']}", {"access_level": "MEMBER"}),
            (f"/api/v1/admin/book-copies/{copy['id']}", {"shelf_location": "A-1"}),
        )
        for path, payload in patches:
            self.assertEqual(
                self.client.patch(path, headers=self.admin_headers, json=payload).status_code,
                200,
            )
        copies = self.client.get(
            f"/api/v1/admin/editions/{edition['id']}/copies",
            headers=self.admin_headers,
        )
        self.assertEqual(copies.json()[0]["shelf_location"], "A-1")

        for path in (
            f"/api/v1/admin/digital-files/{digital['id']}",
            f"/api/v1/admin/book-copies/{copy['id']}",
            f"/api/v1/admin/editions/{edition['id']}",
            f"/api/v1/admin/books/{book['id']}",
            f"/api/v1/admin/authors/{author['id']}",
            f"/api/v1/admin/categories/{category['id']}",
        ):
            self.assertEqual(
                self.client.delete(path, headers=self.admin_headers).status_code, 204
            )


if __name__ == "__main__":
    unittest.main()
