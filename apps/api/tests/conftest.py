import os
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure test settings before importing app
os.environ["ENV"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-32-chars-minimum-abcdef123456"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.api.deps import get_db
from app.core.security import create_session_token, generate_csrf_token
from app.db.base import Base
from app.main import app

# In-memory test engine
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> Generator[None, None, None]:
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers_for_user() -> Any:
    def _create_headers(user_id: str, role: str) -> dict[str, str]:
        token = create_session_token(user_id=user_id, role=role)
        csrf = generate_csrf_token()
        return {
            "Authorization": f"Bearer {token}",
            "X-CSRF-Token": csrf,
            "Cookie": f"sr_session={token}; sr_csrf={csrf}",
        }

    return _create_headers
