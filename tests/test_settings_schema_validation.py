from datetime import datetime
from uuid import uuid4

from fair_platform.extension_sdk import PluginDescriptor, SettingsSchema, TextField
from fair_platform.backend.data.models import (
    Assignment,
    Course,
    Submission,
    SubmissionStatus,
    Workflow,
)
from fair_platform.backend.data.models.submitter import Submitter
from tests.conftest import extension_auth_headers, get_auth_token


def _valid_text_field(default: str = "x") -> dict:
    return {
        "fieldType": "text",
        "label": "Model",
        "description": "Model name.",
        "required": False,
        "default": default,
        "minLength": 1,
        "maxLength": 100,
    }


def _create_workflow_submission_fixture(test_db, *, instructor_id):
    with test_db() as session:
        course = Course(
            id=uuid4(),
            name="Settings Validation Course",
            description="Course for settings validation tests",
            instructor_id=instructor_id,
        )
        workflow = Workflow(
            id=uuid4(),
            course_id=course.id,
            name="Settings Workflow",
            description="workflow for settings validation tests",
            created_by=instructor_id,
            created_at=datetime.utcnow(),
            steps=[],
        )
        assignment = Assignment(
            id=uuid4(),
            course_id=course.id,
            title="Settings Assignment",
            description="assignment under test",
            deadline=None,
            max_grade={"type": "points", "value": 100},
        )
        submitter = Submitter(
            id=uuid4(),
            name="Settings Student",
            email="settings-student@example.com",
            user_id=None,
        )
        submission = Submission(
            id=uuid4(),
            assignment_id=assignment.id,
            submitter_id=submitter.id,
            created_by_id=instructor_id,
            submitted_at=datetime.utcnow(),
            status=SubmissionStatus.submitted,
        )
        session.add_all([course, workflow, assignment, submitter, submission])
        session.commit()
        return workflow.id, submission.id


def test_settings_schema_serializes_through_plugin_descriptor():
    settings = SettingsSchema().add(
        "model",
        TextField(
            fieldType="text",
            label="Model",
            description="Model name",
            required=False,
            default="gpt-4.1",
            minLength=1,
            maxLength=100,
        ),
    )
    plugin = PluginDescriptor(
        plugin_id="mock.grader",
        extension_id="mock.ext",
        plugin_type="grader",
        name="Mock Grader",
        action="plugin.grade.mock",
        settings_schema=settings,
    )

    dumped = plugin.model_dump(by_alias=True, mode="json")
    assert isinstance(dumped["settingsSchema"], dict)
    assert "model" in dumped["settingsSchema"]
    assert dumped["settingsSchema"]["model"]["fieldType"] == "text"


def test_registration_accepts_flat_schema(test_client, extension_client_credentials):
    response = test_client.post(
        "/api/extensions/connect",
        json={
            "extensionId": extension_client_credentials["extension_id"],
            "webhookUrl": "http://localhost:9000/hooks/jobs",
            "metadata": {
                "plugins": [
                    {
                        "pluginId": "mock.valid.schema",
                        "extensionId": extension_client_credentials["extension_id"],
                        "pluginType": "grader",
                        "name": "Valid Schema",
                        "action": "plugin.grade.valid",
                        "settingsSchema": {"model": _valid_text_field("gpt-4.1")},
                    }
                ]
            },
        },
        headers=extension_auth_headers(extension_client_credentials),
    )
    assert response.status_code == 201


def test_registration_rejects_unknown_field_type(test_client, extension_client_credentials):
    response = test_client.post(
        "/api/extensions/connect",
        json={
            "extensionId": extension_client_credentials["extension_id"],
            "webhookUrl": "http://localhost:9000/hooks/jobs",
            "metadata": {
                "plugins": [
                    {
                        "pluginId": "mock.invalid.fieldtype",
                        "extensionId": extension_client_credentials["extension_id"],
                        "pluginType": "grader",
                        "name": "Invalid Field Type",
                        "action": "plugin.grade.invalid",
                        "settingsSchema": {
                            "model": {
                                **_valid_text_field("gpt-4.1"),
                                "fieldType": "unknown",
                            }
                        },
                    }
                ]
            },
        },
        headers=extension_auth_headers(extension_client_credentials),
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["type"] == "invalid_settings_schema"
    assert detail[0]["plugin_id"] == "mock.invalid.fieldtype"


def test_registration_rejects_required_with_default(test_client, extension_client_credentials):
    response = test_client.post(
        "/api/extensions/connect",
        json={
            "extensionId": extension_client_credentials["extension_id"],
            "webhookUrl": "http://localhost:9000/hooks/jobs",
            "metadata": {
                "plugins": [
                    {
                        "pluginId": "mock.invalid.required-default",
                        "extensionId": extension_client_credentials["extension_id"],
                        "pluginType": "grader",
                        "name": "Invalid Required",
                        "action": "plugin.grade.invalid-required",
                        "settingsSchema": {
                            "model": {
                                **_valid_text_field("gpt-4.1"),
                                "required": True,
                            }
                        },
                    }
                ]
            },
        },
        headers=extension_auth_headers(extension_client_credentials),
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["type"] == "invalid_settings_schema"


def test_registration_rejects_type_specific_violation(test_client, extension_client_credentials):
    response = test_client.post(
        "/api/extensions/connect",
        json={
            "extensionId": extension_client_credentials["extension_id"],
            "webhookUrl": "http://localhost:9000/hooks/jobs",
            "metadata": {
                "plugins": [
                    {
                        "pluginId": "mock.invalid.number-range",
                        "extensionId": extension_client_credentials["extension_id"],
                        "pluginType": "grader",
                        "name": "Invalid Number",
                        "action": "plugin.grade.invalid-number",
                        "settingsSchema": {
                            "temperature": {
                                "fieldType": "number",
                                "label": "Temperature",
                                "description": "Sampling value",
                                "required": False,
                                "default": 0.7,
                                "minimum": 2,
                                "maximum": 1,
                            }
                        },
                    }
                ]
            },
        },
        headers=extension_auth_headers(extension_client_credentials),
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["type"] == "invalid_settings_schema"


def test_registration_rejects_unknown_field_keys(test_client, extension_client_credentials):
    response = test_client.post(
        "/api/extensions/connect",
        json={
            "extensionId": extension_client_credentials["extension_id"],
            "webhookUrl": "http://localhost:9000/hooks/jobs",
            "metadata": {
                "plugins": [
                    {
                        "pluginId": "mock.invalid.extra-key",
                        "extensionId": extension_client_credentials["extension_id"],
                        "pluginType": "grader",
                        "name": "Invalid Extra Key",
                        "action": "plugin.grade.invalid-extra",
                        "settingsSchema": {
                            "model": {
                                **_valid_text_field("gpt-4.1"),
                                "unknownKey": "unexpected",
                            }
                        },
                    }
                ]
            },
        },
        headers=extension_auth_headers(extension_client_credentials),
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["type"] == "invalid_settings_schema"


def test_workflow_execution_with_invalid_settings_returns_400(
    test_client, test_db, professor_user
):
    workflow_id, submission_id = _create_workflow_submission_fixture(
        test_db, instructor_id=professor_user.id
    )

    with test_db() as session:
        workflow = session.get(Workflow, workflow_id)
        workflow.steps = [
            {
                "id": "grader-step",
                "order": 0,
                "pluginType": "grader",
                "plugin": {
                    "pluginId": "local.grader",
                    "extensionId": "missing.extension",
                    "name": "Local Grader",
                    "pluginType": "grader",
                    "action": "plugin.grade",
                    "settingsSchema": {
                        "temperature": {
                            "fieldType": "number",
                            "label": "Temperature",
                            "description": "Sampling value",
                            "required": False,
                            "default": 0.7,
                            "minimum": 0,
                            "maximum": 1,
                        }
                    },
                    "settings": {},
                    "id": "local.grader",
                    "type": "grader",
                    "hash": "missing.extension:local.grader",
                    "source": "missing.extension",
                },
                "settings": {"temperature": 2},
            }
        ]
        session.add(workflow)
        session.commit()

    token = get_auth_token(test_client, professor_user.email)
    response = test_client.post(
        "/api/workflow-runs",
        json={"workflowId": str(workflow_id), "submissionIds": [str(submission_id)]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "Settings validation failed for plugin" in response.json()["detail"]


def test_workflow_execution_with_corrupted_schema_returns_422(
    test_client, test_db, professor_user
):
    workflow_id, submission_id = _create_workflow_submission_fixture(
        test_db, instructor_id=professor_user.id
    )

    with test_db() as session:
        workflow = session.get(Workflow, workflow_id)
        workflow.steps = [
            {
                "id": "review-step",
                "order": 0,
                "pluginType": "reviewer",
                "plugin": {
                    "pluginId": "local.reviewer",
                    "extensionId": "missing.extension",
                    "name": "Local Reviewer",
                    "pluginType": "reviewer",
                    "action": "plugin.review",
                    "settingsSchema": {
                        "title": "Legacy Schema",
                        "type": "object",
                        "properties": {},
                    },
                    "settings": {},
                    "id": "local.reviewer",
                    "type": "reviewer",
                    "hash": "missing.extension:local.reviewer",
                    "source": "missing.extension",
                },
                "settings": {},
            }
        ]
        session.add(workflow)
        session.commit()

    token = get_auth_token(test_client, professor_user.email)
    response = test_client.post(
        "/api/workflow-runs",
        json={"workflowId": str(workflow_id), "submissionIds": [str(submission_id)]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422
    assert "corrupted settings_schema" in response.json()["detail"]
