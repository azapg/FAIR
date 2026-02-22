from uuid import uuid4

from fastapi.testclient import TestClient

from fair_platform.backend.api.routers.auth import hash_password
from fair_platform.backend.data.models.user import User
from fair_platform.backend.data.models.user import UserRole
from tests.conftest import create_sample_user_data


class TestAuthenticationFlow:
    """Test the complete user authentication and authorization flow"""

    def test_complete_auth_flow_success(self, test_client: TestClient, admin_user):
        """
        Test the full authentication workflow for a successful case.
        """
        user_data = create_sample_user_data(role=UserRole.student)

        create_response = test_client.post(
            "/api/auth/register",
            json=user_data,
        )

        assert create_response.status_code == 201, (
            f"User creation failed: {create_response.text}"
        )

        created_user = test_client.get(
            "/api/auth/me",
            headers={
                "Authorization": f"Bearer {create_response.json()['access_token']}"
            },
        ).json()

        assert "id" in created_user
        assert created_user["email"] == user_data["email"]
        assert created_user["name"] == user_data["name"]
        assert created_user["role"] == user_data["role"]

        login_response = test_client.post(
            "/api/auth/login",
            data={"username": user_data["email"], "password": "test_password_123"},
        )

        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        login_data = login_response.json()
        assert "access_token" in login_data
        assert "token_type" in login_data
        assert login_data["token_type"] == "bearer"

    def test_login_with_invalid_password_fails(
        self, test_client: TestClient, admin_user
    ):
        """
        Test that login fails with an invalid password (showcasing password validation).
        """
        user_data = create_sample_user_data(role=UserRole.student)

        create_response = test_client.post(
            "/api/auth/register",
            json=user_data,
        )
        assert create_response.status_code == 201, (
            f"User creation failed: {create_response.text}"
        )

        login_response = test_client.post(
            "/api/auth/login",
            data={"username": user_data["email"], "password": "wrong_password"},
        )

        assert login_response.status_code == 401, (
            f"Expected login to fail with invalid password, got {login_response.status_code}: {login_response.text}"
        )
        assert "Invalid credentials" in login_response.json()["detail"]

    def test_login_with_nonexistent_user_fails(self, test_client: TestClient):
        """
        Test that login fails for non-existent users.
        """
        login_response = test_client.post(
            "/api/auth/login",
            data={"username": "nonexistent@example.com", "password": "any_password"},
        )

        assert login_response.status_code == 401, (
            f"Expected login to fail for non-existent user, got {login_response.status_code}: {login_response.text}"
        )
        assert "Invalid credentials" in login_response.json()["detail"]

    def test_register_requires_password_field(self, test_client: TestClient):
        """
        Test that registration now requires a password field.
        """
        user_data_without_password = {
            "name": "Test User",
            "email": "test@example.com",
            "role": "student",
        }

        response = test_client.post(
            "/api/auth/register", json=user_data_without_password
        )

        assert response.status_code == 422, (
            f"Expected validation error without password field, got {response.status_code}: {response.text}"
        )

    def test_protected_route_without_token_fails(
        self, test_client: TestClient, student_user
    ):
        """
        Test that protected routes require authentication.
        """
        response = test_client.get(f"/api/users/{student_user.id}")

        assert response.status_code == 401, (
            f"Expected 401 Unauthorized, got {response.status_code}: {response.text}"
        )

    def test_protected_route_with_invalid_token_fails(
        self, test_client: TestClient, student_user
    ):
        """
        Test that invalid tokens are rejected.
        """
        response = test_client.get(
            f"/api/users/{student_user.id}",
            headers={"Authorization": "Bearer invalid_token_here"},
        )

        assert response.status_code == 401, (
            f"Expected 401 Unauthorized, got {response.status_code}: {response.text}"
        )

    def test_register_does_not_expose_password_hash(self, test_client: TestClient):
        """
        Test that the registration response does not expose the password_hash.
        This is a critical security test.
        """
        user_data = create_sample_user_data(role=UserRole.student)

        response = test_client.post(
            "/api/auth/register",
            json=user_data,
        )

        assert response.status_code == 201, (
            f"User creation failed: {response.text}"
        )

        response_data = response.json()

        # Verify user data is in the response
        assert "user" in response_data, "User data should be in response"
        user = response_data["user"]

        # Verify password_hash is NOT in the response
        assert "password_hash" not in user, (
            "SECURITY VIOLATION: password_hash should never be exposed in API responses"
        )

        # Verify expected fields are present
        assert "id" in user, "User ID should be in response"
        assert "email" in user, "Email should be in response"
        assert "name" in user, "Name should be in response"
        assert "role" in user, "Role should be in response"

    def test_auth_me_capabilities_matrix_by_role_and_mode(self, test_client: TestClient, test_db, monkeypatch):
        scenarios = [
            ("COMMUNITY", UserRole.admin.value, {"manage_users", "cleanup_orphaned_artifacts"}, set()),
            ("ENTERPRISE", UserRole.admin.value, {"manage_users", "cleanup_orphaned_artifacts"}, set()),
            ("COMMUNITY", UserRole.instructor.value, {"create_workflow", "read_workflow_runs"}, {"cleanup_orphaned_artifacts"}),
            ("ENTERPRISE", UserRole.instructor.value, {"create_workflow", "read_workflow_runs"}, {"cleanup_orphaned_artifacts"}),
            ("COMMUNITY", UserRole.user.value, {"join_course", "create_workflow", "read_workflow_runs"}, set()),
            ("ENTERPRISE", UserRole.user.value, {"join_course"}, {"create_workflow", "read_workflow_runs"}),
        ]

        for mode, role, expected_present, expected_missing in scenarios:
            monkeypatch.setenv("FAIR_DEPLOYMENT_MODE", mode)
            email = f"{mode.lower()}-{role}-{uuid4()}@test.com"

            with test_db() as session:
                user = User(
                    id=uuid4(),
                    name=f"{mode} {role}",
                    email=email,
                    role=role,
                    password_hash=hash_password("test_password_123"),
                )
                session.add(user)
                session.commit()

            login_response = test_client.post(
                "/api/auth/login",
                data={"username": email, "password": "test_password_123"},
            )
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]

            me_response = test_client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert me_response.status_code == 200
            payload = me_response.json()
            capabilities = set(payload["capabilities"])

            for capability in expected_present:
                assert capability in capabilities
            for capability in expected_missing:
                assert capability not in capabilities

    def test_auth_me_normalizes_legacy_role_aliases_from_db(self, test_client: TestClient, test_db):
        with test_db() as session:
            legacy_student = User(
                id=uuid4(),
                name="Legacy Student",
                email=f"legacy-student-{uuid4()}@test.com",
                role="student",
                password_hash=hash_password("test_password_123"),
            )
            legacy_professor = User(
                id=uuid4(),
                name="Legacy Professor",
                email=f"legacy-professor-{uuid4()}@test.com",
                role="professor",
                password_hash=hash_password("test_password_123"),
            )
            session.add_all([legacy_student, legacy_professor])
            session.commit()

        for email, expected_role in [
            (legacy_student.email, "user"),
            (legacy_professor.email, "instructor"),
        ]:
            login_response = test_client.post(
                "/api/auth/login",
                data={"username": email, "password": "test_password_123"},
            )
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]

            me_response = test_client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert me_response.status_code == 200
            payload = me_response.json()
            assert payload["role"] == expected_role

    def test_auth_me_preferences_are_loaded_from_user_settings(self, test_client: TestClient, test_db):
        email = f"settings-{uuid4()}@test.com"
        with test_db() as session:
            user = User(
                id=uuid4(),
                name="Settings User",
                email=email,
                role=UserRole.user.value,
                password_hash=hash_password("test_password_123"),
                settings={"preferences": {"interface_mode": "expert"}},
            )
            session.add(user)
            session.commit()

        login_response = test_client.post(
            "/api/auth/login",
            data={"username": email, "password": "test_password_123"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        me_response = test_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200
        payload = me_response.json()
        assert payload["settings"]["preferences"]["interfaceMode"] == "expert"

    def test_user_can_get_and_update_own_settings(self, test_client: TestClient, student_user, test_db):
        login_response = test_client.post(
            "/api/auth/login",
            data={"username": student_user.email, "password": "test_password_123"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        read_response = test_client.get("/api/users/me/settings", headers=headers)
        assert read_response.status_code == 200
        assert read_response.json()["settings"] == {}

        patch_payload = {
            "settings": {
                "preferences": {"interfaceMode": "expert"},
                "ui": {"showTips": False},
            }
        }
        update_response = test_client.patch(
            "/api/users/me/settings",
            json=patch_payload,
            headers=headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["settings"] == patch_payload["settings"]

        verify_response = test_client.get("/api/users/me/settings", headers=headers)
        assert verify_response.status_code == 200
        assert verify_response.json()["settings"] == patch_payload["settings"]

        with test_db() as session:
            refreshed_user = session.get(User, student_user.id)
            assert refreshed_user is not None
            assert refreshed_user.settings == {
                "preferences": {"interface_mode": "expert"},
                "ui": {"show_tips": False},
            }

    def test_user_settings_patch_rejects_conflicting_casing(self, test_client: TestClient, student_user):
        login_response = test_client.post(
            "/api/auth/login",
            data={"username": student_user.email, "password": "test_password_123"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "settings": {
                "preferences": {
                    "interfaceMode": "expert",
                    "interface_mode": "simple",
                },
            }
        }
        update_response = test_client.patch(
            "/api/users/me/settings",
            json=payload,
            headers=headers,
        )
        assert update_response.status_code == 422
        assert "Conflicting keys normalize to 'interface_mode'" in update_response.json()["detail"]
