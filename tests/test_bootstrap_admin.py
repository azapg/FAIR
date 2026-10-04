from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fair_platform.backend.data.database import Base
from fair_platform.backend.data.models import User
from fair_platform.backend.data.models.user import UserRole
from fair_platform.backend.services.bootstrap_admin import (
    bootstrap_admin_from_environment,
)


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_bootstrap_creates_one_verified_admin(
    monkeypatch: pytest.MonkeyPatch,
    session_factory,
):
    monkeypatch.setenv("FAIR_BOOTSTRAP_ADMIN_EMAIL", "Allan@FairGradeProject.org")
    monkeypatch.setenv("FAIR_BOOTSTRAP_ADMIN_NAME", "Allan Zapata")

    assert bootstrap_admin_from_environment(session_factory) is True
    assert bootstrap_admin_from_environment(session_factory) is False

    with session_factory() as session:
        users = session.scalars(select(User)).all()

    assert len(users) == 1
    assert users[0].normalized_email == "allan@fairgradeproject.org"
    assert users[0].name == "Allan Zapata"
    assert users[0].role == UserRole.admin.value
    assert users[0].is_verified is True


def test_bootstrap_refuses_to_create_admin_after_any_user_exists(
    monkeypatch: pytest.MonkeyPatch,
    session_factory,
):
    with session_factory() as session:
        session.add(
            User(
                id=uuid4(),
                name="Existing User",
                email="existing@example.com",
                normalized_email="existing@example.com",
                role=UserRole.user.value,
                password_hash="not-used-by-this-test",
                is_verified=True,
            )
        )
        session.commit()

    monkeypatch.setenv("FAIR_BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")

    assert bootstrap_admin_from_environment(session_factory) is False

    with session_factory() as session:
        created_admin = session.scalar(
            select(User).where(User.email == "admin@example.com")
        )
    assert created_admin is None


def test_bootstrap_rejects_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch,
    session_factory,
):
    monkeypatch.setenv("FAIR_BOOTSTRAP_ADMIN_EMAIL", "not-an-email")

    with pytest.raises(RuntimeError, match="FAIR_BOOTSTRAP_ADMIN_EMAIL is invalid"):
        bootstrap_admin_from_environment(session_factory)
