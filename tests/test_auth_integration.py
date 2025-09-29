from fastapi.testclient import TestClient
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
        
        assert create_response.status_code == 201, f"User creation failed: {create_response.text}"
        
        
        created_user = test_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {create_response.json()['access_token']}"}
        ).json()
        
        assert "id" in created_user
        assert created_user["email"] == user_data["email"]
        assert created_user["name"] == user_data["name"]
        assert created_user["role"] == user_data["role"]
        
        login_response = test_client.post(
            "/api/auth/login",  # Updated to use real login endpoint
            data={
                "username": user_data["email"],
                "password": "test_password_123"  # Use the test password from the fixture
            }
        )
        
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        login_data = login_response.json()
        assert "access_token" in login_data
        assert "token_type" in login_data
        assert login_data["token_type"] == "bearer"

    def test_login_with_invalid_password_fails(self, test_client: TestClient, admin_user):
        """
        Test that login fails with an invalid password (showcasing password validation).
        """
        user_data = create_sample_user_data(role=UserRole.student)
        
        # Register user first
        create_response = test_client.post(
            "/api/auth/register",
            json=user_data,
        )
        assert create_response.status_code == 201, f"User creation failed: {create_response.text}"
        
        # Try to login with wrong password
        login_response = test_client.post(
            "/api/auth/login",
            data={
                "username": user_data["email"],
                "password": "wrong_password"
            }
        )
        
        assert login_response.status_code == 401, f"Expected login to fail with invalid password, got {login_response.status_code}: {login_response.text}"
        assert "Invalid credentials" in login_response.json()["detail"]

    def test_login_with_nonexistent_user_fails(self, test_client: TestClient):
        """
        Test that login fails for non-existent users.
        """
        login_response = test_client.post(
            "/api/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "any_password"
            }
        )
        
        assert login_response.status_code == 401, f"Expected login to fail for non-existent user, got {login_response.status_code}: {login_response.text}"
        assert "Invalid credentials" in login_response.json()["detail"]

    def test_register_requires_password_field(self, test_client: TestClient):
        """
        Test that registration now requires a password field.
        """
        user_data_without_password = {
            "name": "Test User",
            "email": "test@example.com",
            "role": "student"
        }
        
        response = test_client.post("/api/auth/register", json=user_data_without_password)
        
        assert response.status_code == 422, f"Expected validation error without password field, got {response.status_code}: {response.text}"

    
    def test_protected_route_without_token_fails(self, test_client: TestClient, student_user):
        """
        Test that protected routes require authentication.
        """
        response = test_client.get(f"/api/users/{student_user.id}")
        
        assert response.status_code == 401, f"Expected 401 Unauthorized, got {response.status_code}: {response.text}"
    
    def test_protected_route_with_invalid_token_fails(self, test_client: TestClient, student_user):
        """
        Test that invalid tokens are rejected.
        """
        response = test_client.get(
            f"/api/users/{student_user.id}",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401, f"Expected 401 Unauthorized, got {response.status_code}: {response.text}"