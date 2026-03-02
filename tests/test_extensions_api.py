from tests.conftest import extension_auth_headers


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
