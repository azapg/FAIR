from datetime import datetime
from uuid import uuid4

import fair_platform.backend.core.config as config
from fair_platform.backend.core.state_injection import build_initial_state
from fair_platform.backend.data.models.user import User, UserRole


def test_build_initial_state_unauthenticated(monkeypatch):
    monkeypatch.setenv("FAIR_EMAIL_ENABLED", "0")
    monkeypatch.setenv("FAIR_ENFORCE_EMAIL_VERIFICATION", "1")
    monkeypatch.setenv("FAIR_DEPLOYMENT_MODE", "COMMUNITY")
    monkeypatch.setenv("FAIR_BASE_URL", "http://localhost:3000")
    monkeypatch.delenv("FAIR_RESEND_API_KEY", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setattr(config, "RESEND_API_KEY", None)
    monkeypatch.setattr(config, "EMAIL_ENABLED", False)

    state = build_initial_state(None)
    assert state["auth"]["isAuthenticated"] is False
    assert state["auth"]["user"] is None
    assert state["features"]["emailEnabled"] is False
    assert state["features"]["enforceEmailVerification"] is False
    assert state["platform"]["deploymentMode"] == "COMMUNITY"
    assert state["platform"]["baseUrl"] == "http://localhost:3000"
    assert datetime.fromisoformat(state["injectedAt"])


def test_build_initial_state_authenticated_user(monkeypatch):
    monkeypatch.setenv("FAIR_EMAIL_ENABLED", "1")
    monkeypatch.setenv("FAIR_ENFORCE_EMAIL_VERIFICATION", "1")
    monkeypatch.setenv("FAIR_DEPLOYMENT_MODE", "ENTERPRISE")
    monkeypatch.setenv("FAIR_BASE_URL", "https://fair.example.com")
    monkeypatch.delenv("FAIR_RESEND_API_KEY", raising=False)
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setattr(config, "RESEND_API_KEY", None)
    monkeypatch.setattr(config, "EMAIL_ENABLED", True)

    user = User(
        id=uuid4(),
        name="Injected User",
        email="injected@test.com",
        role=UserRole.instructor.value,
        password_hash="x",
        is_verified=True,
        settings={"preferences": {"interface_mode": "expert"}},
    )

    state = build_initial_state(user)
    assert state["auth"]["isAuthenticated"] is True
    assert state["auth"]["user"]["email"] == "injected@test.com"
    assert state["auth"]["user"]["role"] == "instructor"
    assert state["auth"]["user"]["isVerified"] is True
    assert state["auth"]["user"]["settings"]["preferences"]["interfaceMode"] == "expert"
    assert "create_workflow" in state["auth"]["user"]["capabilities"]
    assert state["features"]["emailEnabled"] is True
    assert state["features"]["enforceEmailVerification"] is True
    assert state["platform"]["deploymentMode"] == "ENTERPRISE"
    assert state["platform"]["baseUrl"] == "https://fair.example.com"
