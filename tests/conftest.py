import pytest
import os
import tempfile
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from faker import Faker

from fair_platform.backend.main import app
from fair_platform.backend.data.database import Base, session_dependency
from fair_platform.backend.data.models.user import User, UserRole

fake = Faker()


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        test_db_path = tmp_file.name

    TEST_DATABASE_URL = f"sqlite:///{test_db_path}"

    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def enable_sqlite_fks(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[session_dependency] = override_get_db

    yield TestingSessionLocal

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

    try:
        os.unlink(test_db_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def test_client(test_db):
    """FastAPI test client with test database"""
    return TestClient(app)


@pytest.fixture
def admin_user(test_db):
    """Create an admin user for testing"""
    from fair_platform.backend.api.routers.auth import hash_password
    with test_db() as session:
        user = User(
            id=uuid4(),
            name=fake.name(),
            email="admin@test.com",
            role=UserRole.admin,
            password_hash=hash_password("test_password_123")
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@pytest.fixture
def professor_user(test_db):
    """Create a professor user for testing"""
    from fair_platform.backend.api.routers.auth import hash_password
    with test_db() as session:
        user = User(
            id=uuid4(),
            name=fake.name(),
            email="professor@test.com",
            role=UserRole.professor,
            password_hash=hash_password("test_password_123")
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@pytest.fixture
def student_user(test_db):
    """Create a student user for testing"""
    from fair_platform.backend.api.routers.auth import hash_password
    with test_db() as session:
        user = User(
            id=uuid4(),
            name=fake.name(),
            email="student@test.com",
            role=UserRole.student,
            password_hash=hash_password("test_password_123")
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def get_auth_token(test_client: TestClient, email: str, password: str = "test_password_123") -> str:
    """Helper function to get authentication token for a user by email"""
    login_data = {"username": email, "password": password}
    response = test_client.post("/api/auth/login", data=login_data)

    if response.status_code != 200:
        raise Exception(f"Failed to get auth token: {response.text}")

    return response.json()["access_token"]


def create_sample_user_data(role: UserRole = UserRole.student) -> dict:
    """Helper to create realistic user data for tests"""
    return {
        "name": fake.name(),
        "email": fake.email(),
        "role": role.value,
        "password": "test_password_123",  # TODO: Implement password hashing
    }
