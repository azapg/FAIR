from fastapi.testclient import TestClient
from fair_platform.backend.data.models.user import UserRole
from tests.conftest import create_sample_user_data

# TODO: Separate api/users tests from api/auth tests. Also, be more strict with current auth tests. Do not allow for mock-login nor hashing bypass.

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
            "/api/auth/mock-login", # TODO: Change to real login endpoint when implemented
            data={
                "username": user_data["email"],
                "password": "bruh i am not even hashing passwords yet"
            }
        )
        
        assert login_response.status_code == 200, f"Mock login failed: {login_response.text}"
        login_data = login_response.json()
        assert "access_token" in login_data
        assert "token_type" in login_data
        assert login_data["token_type"] == "bearer"

    
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