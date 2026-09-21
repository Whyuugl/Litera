import os
import unittest

import jwt

os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-at-least-32-characters"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import require_admin
from app.core.database import Base, get_session
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


class AuthenticationTest(unittest.TestCase):
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

    def register(self, email: str = "wahyu@example.com"):
        return self.client.post(
            "/api/v1/auth/register",
            json={"name": "Wahyu", "email": email, "password": "strong-password"},
        )

    def login(self, email: str = "wahyu@example.com"):
        return self.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "strong-password"},
        )

    def test_register_and_duplicate(self) -> None:
        response = self.register("WAHYU@example.com")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["email"], "wahyu@example.com")
        self.assertEqual(response.json()["role"], "USER")
        self.assertNotIn("password_hash", response.json())
        with Session(engine) as session:
            password_hash = session.query(User).one().password_hash
        self.assertTrue(password_hash.startswith("$argon2id$"))
        self.assertNotEqual(password_hash, "strong-password")
        self.assertEqual(self.register().status_code, 409)

    def test_login_success_and_wrong_password(self) -> None:
        self.register()
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["token_type"], "bearer")
        claims = jwt.decode(
            response.json()["access_token"], options={"verify_signature": False}
        )
        self.assertEqual(set(claims), {"sub", "type", "iat", "exp", "jti"})
        self.assertEqual(
            self.client.post(
                "/api/v1/auth/login",
                json={"email": "wahyu@example.com", "password": "wrong-password"},
            ).status_code,
            401,
        )

    def test_inactive_user_cannot_login(self) -> None:
        self.register()
        with Session(engine) as session:
            user = session.query(User).filter_by(email="wahyu@example.com").one()
            user.is_active = False
            session.commit()
        self.assertEqual(self.login().status_code, 403)

    def test_current_user_requires_valid_access_token(self) -> None:
        self.assertEqual(self.client.get("/api/v1/users/me").status_code, 401)
        self.register()
        access = self.login().json()["access_token"]
        response = self.client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {access}"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], "wahyu@example.com")
        self.assertNotIn("password_hash", response.json())

    def test_refresh_rejects_access_and_rotates_once(self) -> None:
        self.register()
        tokens = self.login().json()
        self.assertEqual(
            self.client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": tokens["access_token"]},
            ).status_code,
            401,
        )
        rotated = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        self.assertEqual(rotated.status_code, 200)
        self.assertNotEqual(rotated.json()["refresh_token"], tokens["refresh_token"])
        self.assertEqual(
            self.client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": tokens["refresh_token"]},
            ).status_code,
            401,
        )

    def test_logout_revokes_refresh_session(self) -> None:
        self.register()
        refresh = self.login().json()["refresh_token"]
        self.assertEqual(
            self.client.post(
                "/api/v1/auth/logout", json={"refresh_token": refresh}
            ).status_code,
            204,
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/auth/refresh", json={"refresh_token": refresh}
            ).status_code,
            401,
        )

    def test_admin_authorization(self) -> None:
        user = User(
            name="User",
            email="user@example.com",
            password_hash="unused",
            role=UserRole.USER,
        )
        with self.assertRaises(HTTPException) as error:
            require_admin(user)
        self.assertEqual(error.exception.status_code, 403)
        user.role = UserRole.ADMIN
        self.assertIs(require_admin(user), user)

    def test_health(self) -> None:
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "litera-api"})


if __name__ == "__main__":
    unittest.main()
