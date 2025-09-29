"""
Tests for atomic assignment creation with file uploads.

These tests enforce the atomic operations design from ARTIFACTS_API_IMPLEMENTATION.md
where assignment creation and file uploads happen as a single transaction.
"""

from uuid import uuid4
from datetime import datetime, timedelta
from io import BytesIO
from unittest.mock import patch

from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.artifact import Artifact
from tests.conftest import get_auth_token


class TestAtomicAssignmentCreation:
    """Test atomic assignment creation with file uploads"""
    
    def test_create_assignment_with_files_success(self, test_client, test_db, professor_user):
        """Test successful atomic assignment creation with file uploads"""
        with test_db() as session:
            # Create course first
            course = Course(
                id=uuid4(),
                name="Test Course",
                description="Test course for assignment creation",
                instructor_id=professor_user.id
            )
            session.add(course)
            session.commit()
            course_id = str(course.id)
        
        # Get auth token
        token = get_auth_token(test_client, professor_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Prepare test files
        file1_content = b"This is test file 1 content"
        file2_content = b"This is test file 2 content" 
        
        files = [
            ("files", ("test1.txt", BytesIO(file1_content), "text/plain")),
            ("files", ("test2.pdf", BytesIO(file2_content), "application/pdf"))
        ]
        
        # Assignment data
        form_data = {
            "course_id": course_id,
            "title": "Test Assignment with Files",
            "description": "This assignment has attached files",
            "deadline": (datetime.now() + timedelta(days=7)).isoformat(),
            "max_grade": '{"points": 100}'
        }
        
        # Make atomic request
        response = test_client.post(
            "/api/assignments/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should succeed
        assert response.status_code == 201
        assignment_data = response.json()
        
        # Verify assignment was created
        assert assignment_data["title"] == "Test Assignment with Files"
        assert assignment_data["course_id"] == course_id
        assert "artifacts" in assignment_data
        assert len(assignment_data["artifacts"]) == 2
        
        # Verify artifacts were created with proper ownership
        artifacts = assignment_data["artifacts"]
        for artifact in artifacts:
            assert artifact["creator_id"] == str(professor_user.id)
            assert artifact["status"] == "attached"
            assert artifact["access_level"] == "assignment"
            assert artifact["course_id"] == course_id
            assert artifact["assignment_id"] == assignment_data["id"]
        
        # Verify file names
        file_names = [artifact["title"] for artifact in artifacts]
        assert "test1.txt" in file_names
        assert "test2.pdf" in file_names

    def test_create_assignment_with_files_unauthorized(self, test_client, test_db, student_user):
        """Test that students cannot create assignments"""
        with test_db() as session:
            # Create course with different instructor
            prof_id = uuid4()
            professor = User(
                id=prof_id,
                name="Prof Different",
                email="different@test.com",
                role=UserRole.professor
            )
            session.add(professor)
            
            course = Course(
                id=uuid4(),
                name="Test Course", 
                description="Test course",
                instructor_id=prof_id
            )
            session.add(course)
            session.commit()
            course_id = str(course.id)
        
        # Get student auth token
        token = get_auth_token(test_client, student_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to create assignment
        files = [("files", ("test.txt", BytesIO(b"content"), "text/plain"))]
        form_data = {
            "course_id": course_id,
            "title": "Unauthorized Assignment",
            "description": "Should fail",
            "max_grade": '{"points": 100}'
        }
        
        response = test_client.post(
            "/api/assignments/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should be forbidden
        assert response.status_code == 403

    def test_create_assignment_with_files_invalid_course(self, test_client, test_db, professor_user):
        """Test assignment creation with non-existent course"""
        token = get_auth_token(test_client, professor_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        files = [("files", ("test.txt", BytesIO(b"content"), "text/plain"))]
        form_data = {
            "course_id": str(uuid4()),  # Non-existent course
            "title": "Invalid Course Assignment",
            "description": "Should fail",
            "max_grade": '{"points": 100}'
        }
        
        response = test_client.post(
            "/api/assignments/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should fail with not found
        assert response.status_code == 404

    def test_create_assignment_with_files_course_not_owned(self, test_client, test_db, professor_user):
        """Test professor cannot create assignment in course they don't own"""
        with test_db() as session:
            # Create course with different instructor
            other_prof_id = uuid4()
            other_professor = User(
                id=other_prof_id,
                name="Other Prof",
                email="other@test.com", 
                role=UserRole.professor
            )
            session.add(other_professor)
            
            course = Course(
                id=uuid4(),
                name="Other's Course",
                description="Course owned by other professor",
                instructor_id=other_prof_id
            )
            session.add(course)
            session.commit()
            course_id = str(course.id)
        
        token = get_auth_token(test_client, professor_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        files = [("files", ("test.txt", BytesIO(b"content"), "text/plain"))]
        form_data = {
            "course_id": course_id,
            "title": "Unauthorized Assignment",
            "description": "Should fail",
            "max_grade": '{"points": 100}'
        }
        
        response = test_client.post(
            "/api/assignments/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should be forbidden
        assert response.status_code == 403

    def test_create_assignment_with_no_files(self, test_client, test_db, professor_user):
        """Test assignment creation without files (should still work)"""
        with test_db() as session:
            course = Course(
                id=uuid4(),
                name="Test Course",
                description="Test course",
                instructor_id=professor_user.id
            )
            session.add(course)
            session.commit()
            course_id = str(course.id)
        
        token = get_auth_token(test_client, professor_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        # No files, just assignment data
        form_data = {
            "course_id": course_id,
            "title": "Assignment Without Files",
            "description": "This assignment has no files",
            "max_grade": '{"points": 100}'
        }
        
        response = test_client.post(
            "/api/assignments/create-with-files",
            data=form_data,
            headers=headers
        )
        
        assert response.status_code == 201
        assignment_data = response.json()
        assert assignment_data["title"] == "Assignment Without Files"
        assert len(assignment_data.get("artifacts", [])) == 0

    def test_create_assignment_with_files_large_file_rejection(self, test_client, test_db, professor_user):
        """Test that large files are rejected properly"""
        with test_db() as session:
            course = Course(
                id=uuid4(),
                name="Test Course", 
                description="Test course",
                instructor_id=professor_user.id
            )
            session.add(course)
            session.commit()
            course_id = str(course.id)
        
        token = get_auth_token(test_client, professor_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create large file (simulate file > allowed size)
        large_content = b"x" * (10 * 1024 * 1024)  # 10MB
        files = [("files", ("large.txt", BytesIO(large_content), "text/plain"))]
        
        form_data = {
            "course_id": course_id,
            "title": "Assignment with Large File",
            "description": "Should reject large file",
            "max_grade": '{"points": 100}'
        }
        
        response = test_client.post(
            "/api/assignments/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should reject due to file size
        assert response.status_code == 413  # Payload Too Large

    def test_create_assignment_with_files_invalid_file_type(self, test_client, test_db, professor_user):
        """Test rejection of disallowed file types"""
        with test_db() as session:
            course = Course(
                id=uuid4(),
                name="Test Course",
                description="Test course", 
                instructor_id=professor_user.id
            )
            session.add(course)
            session.commit()
            course_id = str(course.id)
        
        token = get_auth_token(test_client, professor_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Executable file (should be rejected)
        files = [("files", ("malware.exe", BytesIO(b"fake exe"), "application/x-executable"))]
        
        form_data = {
            "course_id": course_id,
            "title": "Assignment with Executable",
            "description": "Should reject executable",
            "max_grade": '{"points": 100}'
        }
        
        response = test_client.post(
            "/api/assignments/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should reject due to file type
        assert response.status_code == 400

    @patch('fair_platform.backend.api.routers.assignments.upload_file')
    def test_create_assignment_with_files_storage_failure_rollback(self, mock_upload, test_client, test_db, professor_user):
        """Test that storage failure triggers proper rollback"""
        with test_db() as session:
            course = Course(
                id=uuid4(),
                name="Test Course",
                description="Test course",
                instructor_id=professor_user.id
            )
            session.add(course)
            session.commit()
            course_id = str(course.id)
        
        # Mock storage failure
        mock_upload.side_effect = Exception("Storage failure")
        
        token = get_auth_token(test_client, professor_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        files = [("files", ("test.txt", BytesIO(b"content"), "text/plain"))]
        form_data = {
            "course_id": course_id,
            "title": "Assignment with Storage Failure",
            "description": "Should rollback on storage failure",
            "max_grade": '{"points": 100}'
        }
        
        response = test_client.post(
            "/api/assignments/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should fail with internal server error
        assert response.status_code == 500
        
        # Verify no assignment was created in database
        with test_db() as session:
            assignments = session.query(Assignment).filter(
                Assignment.title == "Assignment with Storage Failure"
            ).all()
            assert len(assignments) == 0
            
            # Verify no orphaned artifacts were created
            artifacts = session.query(Artifact).filter(
                Artifact.title == "test.txt"
            ).all()
            assert len(artifacts) == 0

    def test_create_assignment_with_files_invalid_json_grade(self, test_client, test_db, professor_user):
        """Test handling of invalid JSON in max_grade field"""
        with test_db() as session:
            course = Course(
                id=uuid4(),
                name="Test Course",
                description="Test course",
                instructor_id=professor_user.id
            )
            session.add(course)
            session.commit()
            course_id = str(course.id)
        
        token = get_auth_token(test_client, professor_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        files = [("files", ("test.txt", BytesIO(b"content"), "text/plain"))]
        form_data = {
            "course_id": course_id,
            "title": "Assignment with Invalid Grade",
            "description": "Should fail validation",
            "max_grade": "invalid json"  # Invalid JSON
        }
        
        response = test_client.post(
            "/api/assignments/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should fail validation
        assert response.status_code == 422

    def test_create_assignment_with_files_missing_required_fields(self, test_client, test_db, professor_user):
        """Test validation of required fields"""
        token = get_auth_token(test_client, professor_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        files = [("files", ("test.txt", BytesIO(b"content"), "text/plain"))]
        
        # Missing course_id
        form_data = {
            "title": "Assignment Missing Course",
            "description": "Should fail validation"
        }
        
        response = test_client.post(
            "/api/assignments/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        assert response.status_code == 422
        
        # Missing title
        form_data = {
            "course_id": str(uuid4()),
            "description": "Should fail validation"
        }
        
        response = test_client.post(
            "/api/assignments/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        assert response.status_code == 422

    def test_create_assignment_with_files_concurrent_requests(self, test_client, test_db, professor_user):
        """Test that concurrent requests don't create inconsistent state"""
        with test_db() as session:
            course = Course(
                id=uuid4(),
                name="Test Course",
                description="Test course for concurrency test",
                instructor_id=professor_user.id
            )
            session.add(course)
            session.commit()
            course_id = str(course.id)
        
        token = get_auth_token(test_client, professor_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Simulate concurrent requests with same assignment title
        files = [("files", ("test.txt", BytesIO(b"content"), "text/plain"))]
        form_data = {
            "course_id": course_id,
            "title": "Concurrent Assignment",
            "description": "Testing concurrency",
            "max_grade": '{"points": 100}'
        }
        
        # Both requests should succeed (no unique constraint on title)
        response1 = test_client.post(
            "/api/assignments/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        response2 = test_client.post(
            "/api/assignments/create-with-files", 
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Both should succeed (unless business rules prevent duplicate titles)
        assert response1.status_code == 201
        assert response2.status_code == 201
        
        # Should have different IDs
        assert response1.json()["id"] != response2.json()["id"]