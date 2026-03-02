from fair_platform.backend.services.job_queue import JobStatus
from tests.conftest import extension_auth_headers, get_auth_token


def test_create_job_returns_202_and_state_is_queued(test_client, extension_client_credentials, student_user):
    user_headers = {"Authorization": f"Bearer {get_auth_token(test_client, student_user.email)}"}
    response = test_client.post(
        "/api/jobs/",
        json={
            "target": extension_client_credentials["extension_id"],
            "payload": {"action": "submission.grade", "params": {"submissionId": "sub-1"}},
            "metadata": {"source": "ui"},
            "jobId": "job-api-1",
        },
        headers=user_headers,
    )
    assert response.status_code == 202
    body = response.json()
    assert body["jobId"] == "job-api-1"
    assert body["status"] == JobStatus.QUEUED

    state_response = test_client.get("/api/jobs/job-api-1", headers=user_headers)
    assert state_response.status_code == 200
    state = state_response.json()
    assert state["jobId"] == "job-api-1"
    assert state["status"] == JobStatus.QUEUED


def test_create_duplicate_job_id_returns_409(test_client, extension_client_credentials, student_user):
    user_headers = {"Authorization": f"Bearer {get_auth_token(test_client, student_user.email)}"}
    payload = {
        "target": extension_client_credentials["extension_id"],
        "payload": {"action": "submission.grade", "params": {"submissionId": "sub-2"}},
        "jobId": "job-dup-1",
    }
    first = test_client.post("/api/jobs/", json=payload, headers=user_headers)
    second = test_client.post("/api/jobs/", json=payload, headers=user_headers)

    assert first.status_code == 202
    assert second.status_code == 409


def test_publish_update_with_status_transition(test_client, extension_client_credentials, student_user):
    user_headers = {"Authorization": f"Bearer {get_auth_token(test_client, student_user.email)}"}
    extension_headers = extension_auth_headers(extension_client_credentials)
    created = test_client.post(
        "/api/jobs/",
        json={
            "target": extension_client_credentials["extension_id"],
            "payload": {"action": "submission.grade", "params": {"submissionId": "sub-3"}},
            "jobId": "job-update-1",
        },
        headers=user_headers,
    )
    assert created.status_code == 202

    updated = test_client.post(
        "/api/jobs/job-update-1/updates",
        json={
            "update": {"event": "progress", "payload": {"percent": 40}},
            "status": JobStatus.RUNNING,
            "details": {"worker": "dispatcher-1"},
        },
        headers=extension_headers,
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["accepted"] is True
    assert body["status"] == JobStatus.RUNNING

    state_response = test_client.get("/api/jobs/job-update-1", headers=user_headers)
    assert state_response.status_code == 200
    state = state_response.json()
    assert state["status"] == JobStatus.RUNNING
    assert state["details"]["worker"] == "dispatcher-1"
    assert state["details"]["owner_extension_id"] == extension_client_credentials["extension_id"]


def test_unknown_job_returns_404_for_state_update_and_stream(test_client, extension_client_credentials, student_user):
    user_headers = {"Authorization": f"Bearer {get_auth_token(test_client, student_user.email)}"}
    extension_headers = extension_auth_headers(extension_client_credentials)
    missing_state = test_client.get("/api/jobs/does-not-exist", headers=user_headers)
    assert missing_state.status_code == 404

    missing_update = test_client.post(
        "/api/jobs/does-not-exist/updates",
        json={"update": {"event": "progress", "payload": {"percent": 1}}},
        headers=extension_headers,
    )
    assert missing_update.status_code == 404

    missing_stream = test_client.get("/api/jobs/does-not-exist/stream", headers=user_headers)
    assert missing_stream.status_code == 404


def test_rubric_create_job_requires_frontend_generate_params(
    test_client,
    extension_client_credentials,
    student_user,
):
    user_headers = {"Authorization": f"Bearer {get_auth_token(test_client, student_user.email)}"}

    invalid = test_client.post(
        "/api/jobs/",
        json={
            "target": extension_client_credentials["extension_id"],
            "payload": {"action": "rubric.create", "params": {"assignment_topic": "Panama Canal"}},
            "jobId": "job-rubric-invalid-params",
        },
        headers=user_headers,
    )
    assert invalid.status_code == 422

    valid = test_client.post(
        "/api/jobs/",
        json={
            "target": extension_client_credentials["extension_id"],
            "payload": {"action": "rubric.create", "params": {"instruction": "Create rubric for essay"}},
            "jobId": "job-rubric-valid-params",
        },
        headers=user_headers,
    )
    assert valid.status_code == 202


def test_rubric_job_result_must_match_generate_response_shape(
    test_client,
    extension_client_credentials,
    student_user,
):
    user_headers = {"Authorization": f"Bearer {get_auth_token(test_client, student_user.email)}"}
    extension_headers = extension_auth_headers(extension_client_credentials)

    created = test_client.post(
        "/api/jobs/",
        json={
            "target": extension_client_credentials["extension_id"],
            "payload": {"action": "rubric.create", "params": {"instruction": "Create rubric"}},
            "jobId": "job-rubric-result-shape",
        },
        headers=user_headers,
    )
    assert created.status_code == 202

    invalid_result = test_client.post(
        "/api/jobs/job-rubric-result-shape/updates",
        json={
            "update": {
                "event": "result",
                "payload": {"data": {"rubric_matrix": {"criteria": []}}},
            },
            "status": JobStatus.COMPLETED,
        },
        headers=extension_headers,
    )
    assert invalid_result.status_code == 422

    valid_result = test_client.post(
        "/api/jobs/job-rubric-result-shape/updates",
        json={
            "update": {
                "event": "result",
                "payload": {
                    "data": {
                        "content": {
                            "levels": ["Poor", "Good"],
                            "criteria": [
                                {
                                    "name": "Clarity",
                                    "weight": 1.0,
                                    "levels": ["Unclear", "Clear"],
                                }
                            ],
                        }
                    }
                },
            },
            "status": JobStatus.COMPLETED,
        },
        headers=extension_headers,
    )
    assert valid_result.status_code == 200
