import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone

os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-characters"
os.environ["MEMBERSHIP_DURATION_DAYS"] = "365"

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import require_active_member
from app.core.database import Base, get_session
from app.core.security import create_access_token
from app.main import app
from app.models import Membership, MembershipStatus, User, UserRole


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def test_session():
    with Session(engine, expire_on_commit=False) as session:
        yield session


class MembershipLifecycleTest(unittest.TestCase):
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
        self.user = self.create_user("user@example.com", UserRole.USER)
        self.admin = self.create_user("admin@example.com", UserRole.ADMIN)

    def create_user(self, email: str, role: UserRole) -> User:
        with Session(engine, expire_on_commit=False) as session:
            user = User(name=email.split("@")[0], email=email, password_hash="unused", role=role)
            session.add(user)
            session.commit()
            return user

    def headers(self, user: User) -> dict[str, str]:
        token, _ = create_access_token(user.id)
        return {"Authorization": f"Bearer {token}"}

    def apply(self, user: User | None = None):
        return self.client.post(
            "/api/v1/memberships/apply", headers=self.headers(user or self.user)
        )

    def approve(self, membership_id: str):
        return self.client.post(
            f"/api/v1/admin/memberships/{membership_id}/approve",
            headers=self.headers(self.admin),
        )

    def test_apply_requires_authentication_and_rejects_duplicates(self) -> None:
        self.assertEqual(self.client.post("/api/v1/memberships/apply").status_code, 401)
        self.assertEqual(self.apply(self.admin).status_code, 403)
        response = self.apply()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "PENDING")
        self.assertIsNone(response.json()["member_number"])
        self.assertEqual(self.apply().status_code, 409)

    def test_current_membership_contract(self) -> None:
        response = self.client.get(
            "/api/v1/memberships/me", headers=self.headers(self.user)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["membership"])
        self.apply()
        response = self.client.get(
            "/api/v1/memberships/me", headers=self.headers(self.user)
        )
        self.assertEqual(response.json()["membership"]["status"], "PENDING")

    def test_user_cannot_access_admin_endpoints(self) -> None:
        membership_id = self.apply().json()["id"]
        headers = self.headers(self.user)
        self.assertEqual(
            self.client.get("/api/v1/admin/memberships", headers=headers).status_code,
            403,
        )
        for action in ("approve", "reject", "suspend"):
            response = self.client.post(
                f"/api/v1/admin/memberships/{membership_id}/{action}",
                headers=headers,
                json={"reason": "not allowed"} if action != "approve" else None,
            )
            self.assertEqual(response.status_code, 403)

    def test_admin_list_filter_search_and_detail(self) -> None:
        membership_id = self.apply().json()["id"]
        headers = self.headers(self.admin)
        response = self.client.get(
            "/api/v1/admin/memberships?status=PENDING&search=user&page=1&page_size=10",
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)
        self.assertEqual(response.json()["items"][0]["user"]["email"], "user@example.com")
        self.assertNotIn("password_hash", response.text)
        self.assertEqual(
            self.client.get(
                f"/api/v1/admin/memberships/{membership_id}", headers=headers
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                "/api/v1/admin/memberships/00000000-0000-0000-0000-000000000000",
                headers=headers,
            ).status_code,
            404,
        )

    def test_admin_approves_pending_membership(self) -> None:
        membership_id = self.apply().json()["id"]
        response = self.approve(membership_id)
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "ACTIVE")
        self.assertTrue(body["member_number"].startswith("LIT-"))
        self.assertIsNotNone(body["approved_at"])
        self.assertIsNotNone(body["expires_at"])
        with Session(engine) as session:
            membership = session.get(Membership, uuid.UUID(body["id"]))
            self.assertEqual(membership.approved_by, self.admin.id)
        self.assertEqual(self.apply().status_code, 409)
        self.assertEqual(self.approve(membership_id).status_code, 409)

    def test_reject_and_reapply(self) -> None:
        membership_id = self.apply().json()["id"]
        response = self.client.post(
            f"/api/v1/admin/memberships/{membership_id}/reject",
            headers=self.headers(self.admin),
            json={"reason": "Information is incomplete."},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "REJECTED")
        self.assertEqual(response.json()["rejection_reason"], "Information is incomplete.")
        self.assertEqual(
            self.client.post(
                f"/api/v1/admin/memberships/{membership_id}/reject",
                headers=self.headers(self.admin),
                json={"reason": "again"},
            ).status_code,
            409,
        )
        reapplied = self.apply()
        self.assertEqual(reapplied.status_code, 200)
        self.assertEqual(reapplied.json()["status"], "PENDING")
        self.assertIsNone(reapplied.json()["rejection_reason"])

    def test_suspend_active_membership(self) -> None:
        membership_id = self.apply().json()["id"]
        self.approve(membership_id)
        response = self.client.post(
            f"/api/v1/admin/memberships/{membership_id}/suspend",
            headers=self.headers(self.admin),
            json={"reason": "Policy violation"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "SUSPENDED")
        self.assertEqual(response.json()["suspension_reason"], "Policy violation")
        self.assertEqual(self.apply().status_code, 409)

    def test_expired_active_membership_can_reapply(self) -> None:
        membership_id = self.apply().json()["id"]
        self.approve(membership_id)
        with Session(engine) as session:
            membership = session.get(Membership, uuid.UUID(membership_id))
            membership.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            session.commit()
        response = self.apply()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "PENDING")
        self.assertIsNone(response.json()["member_number"])
        self.assertIsNone(response.json()["expires_at"])

    def test_active_member_authorization_and_expiration(self) -> None:
        with Session(engine, expire_on_commit=False) as session:
            user = session.get(User, self.user.id)
            with self.assertRaises(HTTPException):
                require_active_member(session, user)

            membership = Membership(user_id=user.id, status=MembershipStatus.PENDING)
            session.add(membership)
            session.commit()
            for blocked_status in (
                MembershipStatus.PENDING,
                MembershipStatus.REJECTED,
                MembershipStatus.SUSPENDED,
            ):
                membership.status = blocked_status
                session.commit()
                with self.assertRaises(HTTPException):
                    require_active_member(session, user)

            membership.status = MembershipStatus.ACTIVE
            membership.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
            session.commit()
            self.assertEqual(require_active_member(session, user).id, membership.id)

            membership.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            session.commit()
            with self.assertRaises(HTTPException):
                require_active_member(session, user)
            session.refresh(membership)
            self.assertEqual(membership.status, MembershipStatus.EXPIRED)


if __name__ == "__main__":
    unittest.main()
