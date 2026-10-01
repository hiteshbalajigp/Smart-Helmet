from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

_test_root = Path(tempfile.mkdtemp(prefix="traffic_violation_tests_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_test_root / 'test.db').as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key-min-16-chars"
os.environ["APP_ENV"] = "development"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = ""

from app.auth.security import hash_password
from app.config.settings import get_settings
from app.database.base import Base
from app.database.models.user import User, UserRole
from app.database.session import SessionLocal, engine
from app.main import app

get_settings.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_user(db_session: Session) -> User:
    existing = db_session.query(User).filter(User.username == "testadmin").first()
    if existing:
        return existing
    user = User(
        username="testadmin",
        email="testadmin@example.com",
        hashed_password=hash_password("TestPass123!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(client: TestClient, admin_user: User) -> str:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": admin_user.username, "password": "TestPass123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]
