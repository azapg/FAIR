from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt
import pytest

from fair_platform.backend.api.routers.auth import create_access_token, get_current_user
from fair_platform.backend.core.config import get_secret_key
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import (
    CapabilityDefinition,
    Execution,
    ExtensionInstallation,
    User,
)
from fair_platform.backend.services.execution_authorization import (
    EXECUTION_TOKEN_AUDIENCE,
    ExecutionAuthorization,
    issue_execution_token,
    require_execution_authorization,
)


def _seed(test_db):
    now = datetime.now(timezone.utc)
    user = User(id=uuid4(), name="Researcher", email=f"{uuid4()}@test", role="user")
    installation = ExtensionInstallation(
        id=uuid4(),
        extension_id="research.agent",
        display_name="Research Agent",
        version="1.0.0",
        delivery_mode="runner",
        status="enabled",
    )
    capability = CapabilityDefinition(
        id=uuid4(),
        installation_id=installation.id,
        capability_id="agent.chat",
        kind="agent",
        version="1.0.0",
        requested_scopes=["artifacts:read"],
        declared_effects=[],
    )
    execution = Execution(
        id=uuid4(),
        root_execution_id=uuid4(),
        attempt=1,
        kind="agent",
        capability_id=capability.capability_id,
        capability_version=capability.version,
        capability_definition_id=capability.id,
        initiated_by_user_id=user.id,
        extension_installation_id=installation.id,
        status="running",
        created_at=now,
    )
    execution.root_execution_id = execution.id
    with test_db() as db:
        db.add_all([user, installation, capability, execution])
        db.commit()
    return user, installation, capability, execution


def _app(test_db):
    app = FastAPI()

    def sessions():
        with test_db() as session:
            yield session

    app.dependency_overrides[session_dependency] = sessions

    @app.get("/execution")
    def execution_endpoint(
        authority: ExecutionAuthorization = Depends(
            require_execution_authorization(("executions:events",))
        ),
    ):
        return {"executionId": str(authority.execution.id)}

    @app.get("/user")
    def user_endpoint(user: User = Depends(get_current_user)):
        return {"userId": str(user.id)}

    return TestClient(app)


def test_execution_token_is_scoped_and_cannot_be_used_as_user_session(test_db):
    user, installation, capability, execution = _seed(test_db)
    issued = issue_execution_token(
        execution=execution,
        installation=installation,
        capability=capability,
        scopes={"executions:events", "artifacts:read"},
    )
    client = _app(test_db)
    headers = {"Authorization": f"Bearer {issued.token}"}

    accepted = client.get("/execution", headers=headers)
    assert accepted.status_code == 200
    assert accepted.json()["executionId"] == str(execution.id)
    assert client.get("/user", headers=headers).status_code == 401


def test_user_session_token_cannot_be_used_as_execution_authority(test_db):
    user, *_ = _seed(test_db)
    token = create_access_token({"sub": str(user.id), "role": user.role})
    client = _app(test_db)

    assert (
        client.get(
            "/execution", headers={"Authorization": f"Bearer {token}"}
        ).status_code
        == 401
    )


def test_execution_token_is_revoked_when_installation_is_disabled(test_db):
    _, installation, capability, execution = _seed(test_db)
    issued = issue_execution_token(
        execution=execution,
        installation=installation,
        capability=capability,
        scopes={"executions:events"},
    )
    with test_db() as db:
        row = db.get(ExtensionInstallation, installation.id)
        row.status = "disabled"
        db.commit()

    response = _app(test_db).get(
        "/execution", headers={"Authorization": f"Bearer {issued.token}"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Execution authority has been revoked"


def test_execution_token_requires_expected_audience(test_db):
    _, installation, capability, execution = _seed(test_db)
    issued = issue_execution_token(
        execution=execution,
        installation=installation,
        capability=capability,
        scopes={"executions:events"},
    )
    claims = jwt.decode(
        issued.token,
        get_secret_key(),
        algorithms=["HS256"],
        audience=EXECUTION_TOKEN_AUDIENCE,
    )
    claims["aud"] = "some-other-service"
    wrong_audience = jwt.encode(
        claims,
        get_secret_key(),
        algorithm="HS256",
        headers={"typ": "fair-execution+jwt"},
    )

    assert (
        _app(test_db)
        .get("/execution", headers={"Authorization": f"Bearer {wrong_audience}"})
        .status_code
        == 401
    )


def test_terminal_execution_cannot_receive_fresh_authority(test_db):
    _, installation, capability, execution = _seed(test_db)
    execution.status = "completed"

    with pytest.raises(ValueError, match="terminal execution"):
        issue_execution_token(
            execution=execution,
            installation=installation,
            capability=capability,
            scopes={"executions:events"},
        )
