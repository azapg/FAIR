from fair_platform.backend.services.job_queue import JobStatus


def test_create_job_returns_202_and_state_is_queued(test_client):
    response = test_client.post(
        "/api/jobs/",
        json={
            "target": "fairgrade.core",
            "payload": {"submissionId": "sub-1"},
            "metadata": {"source": "ui"},
            "jobId": "job-api-1",
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["jobId"] == "job-api-1"
    assert body["status"] == JobStatus.QUEUED

    state_response = test_client.get("/api/jobs/job-api-1")
    assert state_response.status_code == 200
    state = state_response.json()
    assert state["jobId"] == "job-api-1"
    assert state["status"] == JobStatus.QUEUED


def test_create_duplicate_job_id_returns_409(test_client):
    payload = {
        "target": "fairgrade.core",
        "payload": {"submissionId": "sub-2"},
        "jobId": "job-dup-1",
    }
    first = test_client.post("/api/jobs/", json=payload)
    second = test_client.post("/api/jobs/", json=payload)

    assert first.status_code == 202
    assert second.status_code == 409


def test_publish_update_with_status_transition(test_client):
    created = test_client.post(
        "/api/jobs/",
        json={
            "target": "fairgrade.core",
            "payload": {"submissionId": "sub-3"},
            "jobId": "job-update-1",
        },
    )
    assert created.status_code == 202

    updated = test_client.post(
        "/api/jobs/job-update-1/updates",
        json={
            "event": "progress",
            "payload": {"percent": 40},
            "status": JobStatus.RUNNING,
            "details": {"worker": "dispatcher-1"},
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["accepted"] is True
    assert body["status"] == JobStatus.RUNNING

    state_response = test_client.get("/api/jobs/job-update-1")
    assert state_response.status_code == 200
    state = state_response.json()
    assert state["status"] == JobStatus.RUNNING
    assert state["details"] == {"worker": "dispatcher-1"}


def test_unknown_job_returns_404_for_state_update_and_stream(test_client):
    missing_state = test_client.get("/api/jobs/does-not-exist")
    assert missing_state.status_code == 404

    missing_update = test_client.post(
        "/api/jobs/does-not-exist/updates",
        json={"event": "progress", "payload": {"percent": 1}},
    )
    assert missing_update.status_code == 404

    missing_stream = test_client.get("/api/jobs/does-not-exist/stream")
    assert missing_stream.status_code == 404
