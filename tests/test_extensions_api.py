from datetime import datetime, timezone

from fair_platform.backend.data.models import ExtensionClient
from fair_platform.backend.services.extension_auth import hash_extension_secret
from tests.conftest import extension_auth_headers
from tests.conftest import get_auth_token


def test_register_and_list_extensions(test_client, extension_client_credentials):
    response = test_client.post(
        "/api/extensions/connect",
        json={
            "extensionId": extension_client_credentials["extension_id"],
            "webhookUrl": "http://localhost:9000/hooks/jobs",
            "intents": ["rubrics.generate", "chat.reply"],
            "capabilities": ["rubrics", "chat"],
            "requestedScopes": ["jobs:write"],
            "metadata": {"sdk": "python"},
        },
        headers=extension_auth_headers(extension_client_credentials),
    )
    assert response.status_code == 201
    created = response.json()
    assert created["extensionId"] == extension_client_credentials["extension_id"]
    assert created["enabled"] is True
    assert created["requestedScopes"] == ["jobs:write"]
    assert created["metadata"]["approved_scopes"] == ["extensions:connect", "jobs:read", "jobs:write"]
    assert created["metadata"]["effective_scopes"] == ["jobs:write"]

    listed = test_client.get("/api/extensions/")
    assert listed.status_code == 200
    data = listed.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(item["extensionId"] == extension_client_credentials["extension_id"] for item in data)


def test_admin_can_get_and_update_extension_client(
    test_client, admin_user, extension_client_credentials
):
    token = get_auth_token(test_client, admin_user.email)
    headers = {"Authorization": f"Bearer {token}"}

    detail = test_client.get(
        f"/api/extensions/admin/clients/{extension_client_credentials['extension_id']}",
        headers=headers,
    )
    assert detail.status_code == 200
    assert detail.json()["extensionId"] == extension_client_credentials["extension_id"]

    updated = test_client.patch(
        f"/api/extensions/admin/clients/{extension_client_credentials['extension_id']}",
        json={"scopes": ["jobs:read", "jobs:read", "  ", "extensions:connect"], "enabled": False},
        headers=headers,
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["extensionId"] == extension_client_credentials["extension_id"]
    assert body["enabled"] is False
    assert body["scopes"] == ["extensions:connect", "jobs:read"]


def test_register_extension_requires_extensions_connect_scope(test_client, test_db):
    extension_id = "mock.no-connect-scope"
    extension_secret = "no-connect-secret"
    now = datetime.now(timezone.utc)

    with test_db() as session:
        session.add(
            ExtensionClient(
                extension_id=extension_id,
                secret_hash=hash_extension_secret(extension_secret),
                scopes=["jobs:write"],
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

    response = test_client.post(
        "/api/extensions/connect",
        json={
            "extensionId": extension_id,
            "webhookUrl": "http://localhost:9000/hooks/jobs",
        },
        headers={
            "X-FAIR-Extension-Id": extension_id,
            "Authorization": f"Bearer {extension_secret}",
        },
    )
    assert response.status_code == 403
    assert "extensions:connect" in response.json()["detail"]


def test_registered_extension_plugins_are_listed_via_plugins_api(
    test_client, professor_user, extension_client_credentials
):
    register = test_client.post(
        "/api/extensions/connect",
        json={
            "extensionId": extension_client_credentials["extension_id"],
            "webhookUrl": "http://localhost:9000/hooks/jobs",
            "metadata": {
                "plugins": [
                    {
                        "pluginId": "mock.echo.reviewer",
                        "extensionId": extension_client_credentials["extension_id"],
                        "pluginType": "reviewer",
                        "name": "Echo Reviewer",
                        "action": "plugin.review.echo",
                        "settingsSchema": {
                            "title": "Echo Reviewer",
                            "type": "object",
                            "properties": {},
                        },
                    }
                ]
            },
        },
        headers=extension_auth_headers(extension_client_credentials),
    )
    assert register.status_code == 201

    token = get_auth_token(test_client, professor_user.email)
    response = test_client.get(
        "/api/plugins?type_filter=reviewer",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    plugins = response.json()
    assert len(plugins) == 1
    assert plugins[0]["id"] == "mock.echo.reviewer"
    assert plugins[0]["type"] == "reviewer"
    assert plugins[0]["settingsSchema"]["title"] == "Echo Reviewer"
