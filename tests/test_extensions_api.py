def test_register_and_list_extensions(test_client):
    response = test_client.post(
        "/api/extensions/",
        json={
            "extensionId": "fairgrade.core",
            "webhookUrl": "http://localhost:9000/hooks/jobs",
            "intents": ["rubrics.generate", "chat.reply"],
            "capabilities": ["rubrics", "chat"],
            "metadata": {"sdk": "python"},
        },
    )
    assert response.status_code == 201
    created = response.json()
    assert created["extensionId"] == "fairgrade.core"
    assert created["enabled"] is True

    listed = test_client.get("/api/extensions/")
    assert listed.status_code == 200
    data = listed.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(item["extensionId"] == "fairgrade.core" for item in data)
