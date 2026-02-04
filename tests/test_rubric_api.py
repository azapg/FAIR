import pytest
from fastapi.testclient import TestClient

from tests.conftest import get_auth_token


def make_valid_rubric_content():
    return {
        "name": "Essay Rubric",
        "levels": ["Poor", "Fair", "Good", "Excellent"],
        "criteria": [
            {
                "name": "Content",
                "weight": 0.4,
                "levels": ["Missing", "Incomplete", "Adequate", "Comprehensive"]
            },
            {
                "name": "Organization",
                "weight": 0.3,
                "levels": ["Disorganized", "Some structure", "Clear structure", "Excellent flow"]
            },
            {
                "name": "Grammar",
                "weight": 0.3,
                "levels": ["Many errors", "Some errors", "Few errors", "Flawless"]
            }
        ]
    }


class TestRubricAPI:

    def test_create_rubric_as_professor(self, test_client: TestClient, professor_user):
        token = get_auth_token(test_client, professor_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "name": "Test Rubric",
            "content": make_valid_rubric_content()
        }

        response = test_client.post("/api/rubrics/", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Rubric"
        assert data["createdById"] == str(professor_user.id)
        assert "id" in data
        assert "createdAt" in data

    def test_create_rubric_as_admin(self, test_client: TestClient, admin_user):
        token = get_auth_token(test_client, admin_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "name": "Admin Rubric",
            "content": make_valid_rubric_content()
        }

        response = test_client.post("/api/rubrics/", json=payload, headers=headers)
        assert response.status_code == 201

    def test_create_rubric_as_student_fails(self, test_client: TestClient, student_user):
        token = get_auth_token(test_client, student_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "name": "Student Rubric",
            "content": make_valid_rubric_content()
        }

        response = test_client.post("/api/rubrics/", json=payload, headers=headers)
        assert response.status_code == 403

    def test_create_rubric_with_invalid_weights_fails(self, test_client: TestClient, professor_user):
        token = get_auth_token(test_client, professor_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        content = make_valid_rubric_content()
        content["criteria"][0]["weight"] = 0.9

        payload = {"name": "Bad Rubric", "content": content}

        response = test_client.post("/api/rubrics/", json=payload, headers=headers)
        assert response.status_code == 400
        assert "must sum to 1.0" in response.json()["detail"]

    def test_create_rubric_with_mismatched_levels_fails(self, test_client: TestClient, professor_user):
        token = get_auth_token(test_client, professor_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        content = make_valid_rubric_content()
        content["criteria"][0]["levels"] = ["Only", "Two"]

        payload = {"name": "Bad Rubric", "content": content}

        response = test_client.post("/api/rubrics/", json=payload, headers=headers)
        assert response.status_code == 400
        assert "expected 4" in response.json()["detail"]

    def test_list_rubrics_professor_sees_own(self, test_client: TestClient, professor_user):
        token = get_auth_token(test_client, professor_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        payload = {"name": "Prof Rubric", "content": make_valid_rubric_content()}
        test_client.post("/api/rubrics/", json=payload, headers=headers)

        response = test_client.get("/api/rubrics/", headers=headers)
        assert response.status_code == 200
        rubrics = response.json()
        assert len(rubrics) == 1
        assert rubrics[0]["name"] == "Prof Rubric"

    def test_list_rubrics_admin_sees_all(self, test_client: TestClient, admin_user, professor_user):
        prof_token = get_auth_token(test_client, professor_user.email)
        admin_token = get_auth_token(test_client, admin_user.email)

        test_client.post(
            "/api/rubrics/",
            json={"name": "Prof Rubric", "content": make_valid_rubric_content()},
            headers={"Authorization": f"Bearer {prof_token}"}
        )
        test_client.post(
            "/api/rubrics/",
            json={"name": "Admin Rubric", "content": make_valid_rubric_content()},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        response = test_client.get(
            "/api/rubrics/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        rubrics = response.json()
        assert len(rubrics) == 2

    def test_get_rubric_by_id(self, test_client: TestClient, professor_user):
        token = get_auth_token(test_client, professor_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        create_response = test_client.post(
            "/api/rubrics/",
            json={"name": "Get Test", "content": make_valid_rubric_content()},
            headers=headers
        )
        rubric_id = create_response.json()["id"]

        response = test_client.get(f"/api/rubrics/{rubric_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test"

    def test_get_rubric_not_found(self, test_client: TestClient, professor_user):
        token = get_auth_token(test_client, professor_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        response = test_client.get(
            "/api/rubrics/00000000-0000-0000-0000-000000000000",
            headers=headers
        )
        assert response.status_code == 404

    def test_get_rubric_unauthorized(self, test_client: TestClient, professor_user, student_user):
        prof_token = get_auth_token(test_client, professor_user.email)
        student_token = get_auth_token(test_client, student_user.email)

        create_response = test_client.post(
            "/api/rubrics/",
            json={"name": "Private Rubric", "content": make_valid_rubric_content()},
            headers={"Authorization": f"Bearer {prof_token}"}
        )
        rubric_id = create_response.json()["id"]

        response = test_client.get(
            f"/api/rubrics/{rubric_id}",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert response.status_code == 403

    def test_delete_rubric_owner(self, test_client: TestClient, professor_user):
        token = get_auth_token(test_client, professor_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        create_response = test_client.post(
            "/api/rubrics/",
            json={"name": "Delete Me", "content": make_valid_rubric_content()},
            headers=headers
        )
        rubric_id = create_response.json()["id"]

        delete_response = test_client.delete(f"/api/rubrics/{rubric_id}", headers=headers)
        assert delete_response.status_code == 204

        get_response = test_client.get(f"/api/rubrics/{rubric_id}", headers=headers)
        assert get_response.status_code == 404

    def test_delete_rubric_admin(self, test_client: TestClient, admin_user, professor_user):
        prof_token = get_auth_token(test_client, professor_user.email)
        admin_token = get_auth_token(test_client, admin_user.email)

        create_response = test_client.post(
            "/api/rubrics/",
            json={"name": "Prof Rubric", "content": make_valid_rubric_content()},
            headers={"Authorization": f"Bearer {prof_token}"}
        )
        rubric_id = create_response.json()["id"]

        delete_response = test_client.delete(
            f"/api/rubrics/{rubric_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert delete_response.status_code == 204

    def test_delete_rubric_unauthorized(self, test_client: TestClient, professor_user, student_user):
        prof_token = get_auth_token(test_client, professor_user.email)
        student_token = get_auth_token(test_client, student_user.email)

        create_response = test_client.post(
            "/api/rubrics/",
            json={"name": "Protected Rubric", "content": make_valid_rubric_content()},
            headers={"Authorization": f"Bearer {prof_token}"}
        )
        rubric_id = create_response.json()["id"]

        delete_response = test_client.delete(
            f"/api/rubrics/{rubric_id}",
            headers={"Authorization": f"Bearer {student_token}"}
        )
        assert delete_response.status_code == 403

    def test_unauthenticated_request_fails(self, test_client: TestClient):
        response = test_client.get("/api/rubrics/")
        assert response.status_code == 401
