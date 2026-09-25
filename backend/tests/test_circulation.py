import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone

os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-characters"
os.environ["LOAN_DURATION_DAYS"] = "14"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_session
from app.core.security import create_access_token
from app.main import app
from app.models import (
    Author,
    Book,
    BookCopy,
    BookCopyStatus,
    BookStatus,
    BookType,
    Category,
    Edition,
    Loan,
    LoanStatus,
    Membership,
    MembershipStatus,
    Reservation,
    ReservationStatus,
    User,
    UserRole,
)


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def test_session():
    with Session(engine, expire_on_commit=False) as session:
        yield session


class CirculationApiTest(unittest.TestCase):
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
            self.admin = User(name="Admin", email="admin@example.com", password_hash="x", role=UserRole.ADMIN)
            self.member = User(name="Member", email="member@example.com", password_hash="x")
            self.other = User(name="Other", email="other@example.com", password_hash="x")
            self.regular = User(name="Regular", email="regular@example.com", password_hash="x")
            session.add_all([self.admin, self.member, self.other, self.regular])
            session.flush()
            expires = datetime.now(timezone.utc) + timedelta(days=30)
            session.add_all([
                Membership(user_id=self.member.id, status=MembershipStatus.ACTIVE, expires_at=expires),
                Membership(user_id=self.other.id, status=MembershipStatus.ACTIVE, expires_at=expires),
            ])
            category = Category(name="Programming", slug="programming")
            author = Author(name="Robert Martin")
            session.add_all([category, author])
            session.flush()
            book = Book(
                category_id=category.id,
                authors=[author],
                title="Clean Code",
                slug="clean-code",
                language="en",
                book_type=BookType.EDUCATIONAL,
                status=BookStatus.PUBLISHED,
                created_by=self.admin.id,
            )
            session.add(book)
            session.flush()
            self.edition = Edition(book_id=book.id, isbn="ISBN-1")
            self.empty_edition = Edition(book_id=book.id, isbn="ISBN-EMPTY")
            session.add_all([self.edition, self.empty_edition])
            session.flush()
            self.copy = BookCopy(edition_id=self.edition.id, barcode="LIT-0001")
            self.bad_copy = BookCopy(
                edition_id=self.edition.id,
                barcode="LIT-0002",
                status=BookCopyStatus.MAINTENANCE,
            )
            session.add_all([self.copy, self.bad_copy])
            session.commit()

    def headers(self, user: User) -> dict[str, str]:
        token, _ = create_access_token(user.id)
        return {"Authorization": f"Bearer {token}"}

    def reserve(self, user: User | None = None, edition_id=None):
        return self.client.post(
            "/api/v1/reservations",
            headers=self.headers(user or self.member),
            json={"edition_id": str(edition_id or self.edition.id)},
        )

    def mark_ready(self, reservation_id: str):
        return self.client.post(
            f"/api/v1/admin/reservations/{reservation_id}/ready",
            headers=self.headers(self.admin),
        )

    def checkout(self, *, user=None, copy_id=None, reservation_id=None, actor=None):
        return self.client.post(
            "/api/v1/admin/loans/checkout",
            headers=self.headers(actor or self.admin),
            json={
                "user_id": str((user or self.member).id),
                "book_copy_id": str(copy_id or self.copy.id),
                "reservation_id": reservation_id,
            },
        )

    def test_reservation_authorization_validation_ownership_and_cancel(self) -> None:
        self.assertEqual(self.reserve(self.regular).status_code, 403)
        with Session(engine) as session:
            membership = session.query(Membership).filter_by(user_id=self.member.id).one()
            membership.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            session.commit()
        self.assertEqual(self.reserve().status_code, 403)
        with Session(engine) as session:
            membership = session.query(Membership).filter_by(user_id=self.member.id).one()
            membership.status = MembershipStatus.ACTIVE
            membership.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
            session.commit()

        self.assertEqual(self.reserve(edition_id=uuid.uuid4()).status_code, 404)
        self.assertEqual(self.reserve(edition_id=self.empty_edition.id).status_code, 409)
        created = self.reserve()
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["queue_position"], 1)
        self.assertEqual(self.reserve().status_code, 409)
        reservation_id = created.json()["id"]
        self.assertEqual(
            self.client.get(
                f"/api/v1/reservations/{reservation_id}", headers=self.headers(self.other)
            ).status_code,
            404,
        )
        cancelled = self.client.delete(
            f"/api/v1/reservations/{reservation_id}", headers=self.headers(self.member)
        )
        self.assertEqual(cancelled.status_code, 204)
        with Session(engine) as session:
            self.assertEqual(session.get(Reservation, uuid.UUID(reservation_id)).status, ReservationStatus.CANCELLED)

        first = self.reserve().json()
        second = self.reserve(self.other).json()
        self.assertEqual((first["queue_position"], second["queue_position"]), (1, 2))
        self.assertEqual(self.mark_ready(second["id"]).status_code, 409)

    def test_admin_checkout_is_atomic_and_fulfills_reservation(self) -> None:
        with Session(engine) as session:
            membership = session.query(Membership).filter_by(user_id=self.member.id).one()
            membership.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            session.commit()
        self.assertEqual(self.checkout().status_code, 409)
        with Session(engine) as session:
            membership = session.query(Membership).filter_by(user_id=self.member.id).one()
            membership.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            session.commit()
        reservation = self.reserve().json()
        self.assertEqual(
            self.checkout(actor=self.member).status_code,
            403,
        )
        ready = self.mark_ready(reservation["id"])
        self.assertEqual(ready.status_code, 200, ready.text)
        loan = self.checkout(reservation_id=reservation["id"])
        self.assertEqual(loan.status_code, 201, loan.text)
        body = loan.json()
        due = datetime.fromisoformat(body["due_at"])
        borrowed = datetime.fromisoformat(body["borrowed_at"])
        self.assertEqual((due - borrowed).days, 14)
        self.assertEqual(body["processed_by"], str(self.admin.id))

        with Session(engine) as session:
            copy = session.get(BookCopy, self.copy.id)
            saved = session.get(Reservation, uuid.UUID(reservation["id"]))
            self.assertEqual(copy.status, BookCopyStatus.BORROWED)
            self.assertEqual(saved.status, ReservationStatus.FULFILLED)
            self.assertIsNotNone(saved.fulfilled_at)
        self.assertEqual(self.checkout().status_code, 409)
        self.assertEqual(self.checkout(copy_id=self.bad_copy.id).status_code, 409)
        returned = self.client.post(
            f"/api/v1/admin/loans/{body['id']}/return", headers=self.headers(self.admin)
        )
        self.assertEqual(returned.status_code, 200)
        with Session(engine) as session:
            self.assertEqual(session.get(BookCopy, self.copy.id).status, BookCopyStatus.AVAILABLE)

    def test_return_promotes_queue_and_overdue_and_scoped_lists(self) -> None:
        first = self.reserve().json()
        self.mark_ready(first["id"])
        loan = self.checkout(reservation_id=first["id"]).json()
        second = self.reserve(self.other).json()

        with Session(engine) as session:
            saved = session.get(Loan, uuid.UUID(loan["id"]))
            saved.due_at = datetime.now(timezone.utc) - timedelta(days=2)
            session.commit()
        mine = self.client.get("/api/v1/loans/me?view=overdue", headers=self.headers(self.member))
        self.assertEqual(mine.status_code, 200)
        self.assertEqual(mine.json()[0]["status"], "OVERDUE")
        self.assertEqual(
            self.client.get(f"/api/v1/loans/{loan['id']}", headers=self.headers(self.other)).status_code,
            404,
        )

        returned = self.client.post(
            f"/api/v1/admin/loans/{loan['id']}/return", headers=self.headers(self.admin)
        )
        self.assertEqual(returned.status_code, 200, returned.text)
        self.assertEqual(returned.json()["status"], "RETURNED")
        self.assertIsNotNone(returned.json()["returned_at"])
        self.assertEqual(
            self.client.post(
                f"/api/v1/admin/loans/{loan['id']}/return", headers=self.headers(self.admin)
            ).status_code,
            409,
        )
        with Session(engine) as session:
            copy = session.get(BookCopy, self.copy.id)
            queued = session.get(Reservation, uuid.UUID(second["id"]))
            self.assertEqual(copy.status, BookCopyStatus.RESERVED)
            self.assertEqual(queued.status, ReservationStatus.READY)
            self.assertEqual(queued.book_copy_id, self.copy.id)

        admin_loans = self.client.get(
            "/api/v1/admin/loans?status=RETURNED&search=Clean", headers=self.headers(self.admin)
        )
        self.assertEqual(admin_loans.json()["total"], 1)
        admin_reservations = self.client.get(
            "/api/v1/admin/reservations?status=READY&search=Other", headers=self.headers(self.admin)
        )
        self.assertEqual(admin_reservations.json()["total"], 1)

    def test_database_rejects_duplicate_active_transactions(self) -> None:
        now = datetime.now(timezone.utc)
        with Session(engine) as session:
            session.add(Loan(
                user_id=self.member.id,
                book_copy_id=self.copy.id,
                borrowed_at=now,
                due_at=now + timedelta(days=14),
                status=LoanStatus.BORROWED,
            ))
            session.commit()
            session.add(Loan(
                user_id=self.other.id,
                book_copy_id=self.copy.id,
                borrowed_at=now,
                due_at=now + timedelta(days=14),
                status=LoanStatus.BORROWED,
            ))
            with self.assertRaises(IntegrityError):
                session.commit()
            session.rollback()

        first = self.reserve()
        self.assertEqual(first.status_code, 409)  # active loan makes reservation meaningless


if __name__ == "__main__":
    unittest.main()
