"""
Tests for atomic submission creation with file uploads.

These tests enforce the atomic submission creation design from 
ARTIFACTS_API_IMPLEMENTATION.md where submission creation and file uploads 
happen as a single transaction, with proper permission validation.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from io import BytesIO
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.artifact import Artifact
from fair_platform.backend.data.models.submission import Submission
from tests.conftest import get_auth_token


class TestAtomicSubmissionCreation:
    """Test atomic submission creation with file uploads"""
    
    def setup_test_assignment(self, test_db):
        """Create test assignment for submission tests"""
        with test_db() as session:
            # Create professor and course
            prof_id = uuid4()
            professor = User(
                id=prof_id,
                name="Professor",
                email="prof@test.com",
                role=UserRole.professor
            )
            
            student_id = uuid4()
            student = User(
                id=student_id,
                name="Student",
                email="student@test.com",
                role=UserRole.student
            )
            
            session.add_all([professor, student])
            
            course_id = uuid4()
            course = Course(
                id=course_id,
                name="Test Course",
                description="Test course for submissions",
                instructor_id=prof_id
            )
            session.add(course)
            
            assignment_id = uuid4()
            assignment = Assignment(
                id=assignment_id,
                course_id=course_id,
                title="Test Assignment",
                description="Assignment for submission testing",
                deadline=datetime.now() + timedelta(days=7),
                max_grade={"points": 100}
            )
            session.add(assignment)
            session.commit()
            
            return {
                "professor": professor,
                "student": student,
                "course": course,
                "assignment": assignment
            }

    def test_create_submission_with_files_success(self, test_client, test_db):
        """Test successful atomic submission creation with file uploads"""
        data = self.setup_test_assignment(test_db)
        
        # Get student auth token
        token = get_auth_token(test_client, data["student"])
        headers = {"Authorization": f"Bearer {token}"}
        
        # Prepare test files
        file1_content = b"This is my submission file 1"
        file2_content = b"This is my submission file 2"
        
        files = [
            ("files", ("submission1.txt", BytesIO(file1_content), "text/plain")),
            ("files", ("submission2.pdf", BytesIO(file2_content), "application/pdf"))
        ]
        
        # Submission data
        form_data = {
            "assignment_id": str(data["assignment"].id),
            "submitter_id": str(data["student"].id)
        }
        
        # Make atomic submission request
        response = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should succeed
        assert response.status_code == 201
        submission_data = response.json()
        
        # Verify submission was created
        assert submission_data["assignment_id"] == str(data["assignment"].id)
        assert submission_data["submitter_id"] == str(data["student"].id)
        assert submission_data["status"] == "submitted"
        assert "artifacts" in submission_data
        assert len(submission_data["artifacts"]) == 2
        
        # Verify artifacts were created with proper ownership
        artifacts = submission_data["artifacts"]
        for artifact in artifacts:
            assert artifact["creator_id"] == str(data["student"].id)
            assert artifact["status"] == "attached"
            assert artifact["access_level"] == "assignment"
            assert artifact["course_id"] == str(data["course"].id)
            assert artifact["assignment_id"] == str(data["assignment"].id)
        
        # Verify file names
        file_names = [artifact["title"] for artifact in artifacts]
        assert "submission1.txt" in file_names
        assert "submission2.pdf" in file_names

    def test_create_submission_without_files(self, test_client, test_db):
        """Test submission creation without files (should still work)"""
        data = self.setup_test_assignment(test_db)
        
        token = get_auth_token(test_client, data["student"])
        headers = {"Authorization": f"Bearer {token}"}
        
        # No files, just submission data
        form_data = {
            "assignment_id": str(data["assignment"].id),
            "submitter_id": str(data["student"].id)
        }
        
        response = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            headers=headers
        )
        
        assert response.status_code == 201
        submission_data = response.json()
        assert submission_data["assignment_id"] == str(data["assignment"].id)
        assert len(submission_data.get("artifacts", [])) == 0

    def test_create_submission_student_can_only_submit_for_themselves(self, test_client, test_db):
        """Test that students can only create submissions for themselves"""
        data = self.setup_test_assignment(test_db)
        
        # Create another student
        with test_db() as session:
            other_student = User(
                id=uuid4(),
                name="Other Student",
                email="other@test.com",
                role=UserRole.student
            )
            session.add(other_student)
            session.commit()
            other_student_id = other_student.id
        
        # First student tries to submit for second student
        token = get_auth_token(test_client, data["student"])
        headers = {"Authorization": f"Bearer {token}"}
        
        files = [("files", ("test.txt", BytesIO(b"content"), "text/plain"))]
        form_data = {
            "assignment_id": str(data["assignment"].id),
            "submitter_id": str(other_student_id)  # Different student
        }
        
        response = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should be forbidden
        assert response.status_code == 403

    def test_create_submission_professor_can_submit_for_students(self, test_client, test_db):
        """Test that course professors can create submissions for their students"""
        data = self.setup_test_assignment(test_db)
        
        # Professor creates submission for student
        token = get_auth_token(test_client, data["professor"])
        headers = {"Authorization": f"Bearer {token}"}
        
        files = [("files", ("prof_uploaded.txt", BytesIO(b"content"), "text/plain"))]
        form_data = {
            "assignment_id": str(data["assignment"].id),
            "submitter_id": str(data["student"].id)
        }
        
        response = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should succeed
        assert response.status_code == 201
        submission_data = response.json()
        assert submission_data["submitter_id"] == str(data["student"].id)
        
        # Artifacts should still be owned by the submitter (student), not professor
        artifacts = submission_data["artifacts"]
        for artifact in artifacts:
            assert artifact["creator_id"] == str(data["student"].id)

    def test_create_submission_professor_cannot_submit_for_other_course_students(self, test_client, test_db):
        """Test that professors cannot submit for students in courses they don't teach"""
        data = self.setup_test_assignment(test_db)
        
        # Create another professor and student
        with test_db() as session:
            other_prof = User(
                id=uuid4(),
                name="Other Professor",
                email="other_prof@test.com",
                role=UserRole.professor
            )
            
            other_student = User(
                id=uuid4(),
                name="Other Student",
                email="other_student@test.com",
                role=UserRole.student
            )
            
            session.add_all([other_prof, other_student])
            session.commit()
            other_prof_id = other_prof.id
            other_student_id = other_student.id
        
        # Other professor tries to submit for student in first professor's course
        token = get_auth_token(test_client, data["professor"])  # Use different professor
        headers = {"Authorization": f"Bearer {token}"}
        
        files = [("files", ("test.txt", BytesIO(b"content"), "text/plain"))]
        form_data = {
            "assignment_id": str(data["assignment"].id),
            "submitter_id": str(other_student_id)
        }
        
        response = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should be forbidden
        assert response.status_code == 403

    def test_create_submission_invalid_assignment(self, test_client, test_db):
        """Test submission creation with non-existent assignment"""
        data = self.setup_test_assignment(test_db)
        
        token = get_auth_token(test_client, data["student"])
        headers = {"Authorization": f"Bearer {token}"}
        
        files = [("files", ("test.txt", BytesIO(b"content"), "text/plain"))]
        form_data = {
            "assignment_id": str(uuid4()),  # Non-existent assignment
            "submitter_id": str(data["student"].id)
        }
        
        response = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should fail with not found
        assert response.status_code == 404

    def test_create_submission_past_deadline(self, test_client, test_db):
        """Test submission creation after assignment deadline"""
        with test_db() as session:
            # Create assignment with past deadline
            prof_id = uuid4()
            professor = User(
                id=prof_id,
                name="Professor",
                email="prof@test.com",
                role=UserRole.professor
            )
            
            student_id = uuid4()
            student = User(
                id=student_id,
                name="Student",
                email="student@test.com",
                role=UserRole.student
            )
            
            session.add_all([professor, student])
            
            course_id = uuid4()
            course = Course(
                id=course_id,
                name="Test Course",
                description="Test course",
                instructor_id=prof_id
            )
            session.add(course)
            
            assignment_id = uuid4()
            assignment = Assignment(
                id=assignment_id,
                course_id=course_id,
                title="Past Due Assignment",
                description="Assignment with past deadline",
                deadline=datetime.now() - timedelta(days=1),  # Past deadline
                max_grade={"points": 100}
            )
            session.add(assignment)
            session.commit()
        
        token = get_auth_token(test_client, student)
        headers = {"Authorization": f"Bearer {token}"}
        
        files = [("files", ("late.txt", BytesIO(b"late submission"), "text/plain"))]
        form_data = {
            "assignment_id": str(assignment_id),
            "submitter_id": str(student_id)
        }
        
        response = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should fail with appropriate error
        assert response.status_code == 400  # Or 409 for business rule violation
        assert "deadline" in response.json()["detail"].lower()

    def test_create_submission_duplicate_submission(self, test_client, test_db):
        """Test handling of duplicate submissions by same student"""
        data = self.setup_test_assignment(test_db)
        
        token = get_auth_token(test_client, data["student"])
        headers = {"Authorization": f"Bearer {token}"}
        
        files = [("files", ("first.txt", BytesIO(b"first submission"), "text/plain"))]
        form_data = {
            "assignment_id": str(data["assignment"].id),
            "submitter_id": str(data["student"].id)
        }
        
        # First submission should succeed
        response1 = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        assert response1.status_code == 201
        
        # Second submission by same student
        files2 = [("files", ("second.txt", BytesIO(b"second submission"), "text/plain"))]
        
        response2 = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            files=files2,
            headers=headers
        )
        
        # Depending on business rules:
        # - Could succeed (allows multiple submissions)
        # - Could fail (only one submission per student)
        # - Could replace previous submission
        assert response2.status_code in [201, 409]  # Created or Conflict

    def test_create_submission_large_file_rejection(self, test_client, test_db):
        """Test that large files are rejected properly"""
        data = self.setup_test_assignment(test_db)
        
        token = get_auth_token(test_client, data["student"])
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create large file (simulate file > allowed size)
        large_content = b"x" * (10 * 1024 * 1024)  # 10MB
        files = [("files", ("large.txt", BytesIO(large_content), "text/plain"))]
        
        form_data = {
            "assignment_id": str(data["assignment"].id),
            "submitter_id": str(data["student"].id)
        }
        
        response = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should reject due to file size
        assert response.status_code == 413  # Payload Too Large

    def test_create_submission_invalid_file_type(self, test_client, test_db):
        """Test rejection of disallowed file types"""
        data = self.setup_test_assignment(test_db)
        
        token = get_auth_token(test_client, data["student"])
        headers = {"Authorization": f"Bearer {token}"}
        
        # Executable file (should be rejected)
        files = [("files", ("malware.exe", BytesIO(b"fake exe"), "application/x-executable"))]
        
        form_data = {
            "assignment_id": str(data["assignment"].id),
            "submitter_id": str(data["student"].id)
        }
        
        response = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should reject due to file type
        assert response.status_code == 400

    @patch('fair_platform.backend.api.routers.submissions.upload_file')
    def test_create_submission_storage_failure_rollback(self, mock_upload, test_client, test_db):
        """Test that storage failure triggers proper rollback"""
        data = self.setup_test_assignment(test_db)
        
        # Mock storage failure
        mock_upload.side_effect = Exception("Storage failure")
        
        token = get_auth_token(test_client, data["student"])
        headers = {"Authorization": f"Bearer {token}"}
        
        files = [("files", ("test.txt", BytesIO(b"content"), "text/plain"))]
        form_data = {
            "assignment_id": str(data["assignment"].id),
            "submitter_id": str(data["student"].id)
        }
        
        response = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should fail with internal server error
        assert response.status_code == 500
        
        # Verify no submission was created in database
        with test_db() as session:
            submissions = session.query(Submission).filter(
                Submission.assignment_id == data["assignment"].id,
                Submission.submitter_id == data["student"].id
            ).all()
            assert len(submissions) == 0
            
            # Verify no orphaned artifacts were created
            artifacts = session.query(Artifact).filter(
                Artifact.title == "test.txt"
            ).all()
            assert len(artifacts) == 0

    def test_create_submission_missing_required_fields(self, test_client, test_db):
        """Test validation of required fields"""
        data = self.setup_test_assignment(test_db)
        
        token = get_auth_token(test_client, data["student"])
        headers = {"Authorization": f"Bearer {token}"}
        
        files = [("files", ("test.txt", BytesIO(b"content"), "text/plain"))]
        
        # Missing assignment_id
        form_data = {
            "submitter_id": str(data["student"].id)
        }
        
        response = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        assert response.status_code == 422
        
        # Missing submitter_id
        form_data = {
            "assignment_id": str(data["assignment"].id)
        }
        
        response = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        assert response.status_code == 422

    def test_create_submission_invalid_submitter_id(self, test_client, test_db):
        """Test submission creation with non-existent submitter"""
        data = self.setup_test_assignment(test_db)
        
        token = get_auth_token(test_client, data["professor"])  # Professor token
        headers = {"Authorization": f"Bearer {token}"}
        
        files = [("files", ("test.txt", BytesIO(b"content"), "text/plain"))]
        form_data = {
            "assignment_id": str(data["assignment"].id),
            "submitter_id": str(uuid4())  # Non-existent user
        }
        
        response = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        # Should fail with not found
        assert response.status_code == 404

    def test_submission_artifact_ownership_and_permissions(self, test_client, test_db):
        """Test that submission artifacts have correct ownership and permissions"""
        data = self.setup_test_assignment(test_db)
        
        token = get_auth_token(test_client, data["student"])
        headers = {"Authorization": f"Bearer {token}"}
        
        files = [("files", ("submission.txt", BytesIO(b"my work"), "text/plain"))]
        form_data = {
            "assignment_id": str(data["assignment"].id),
            "submitter_id": str(data["student"].id)
        }
        
        response = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        assert response.status_code == 201
        submission_data = response.json()
        
        # Get the created artifact
        artifact = submission_data["artifacts"][0]
        artifact_id = artifact["id"]
        
        # Test student can access their submission artifact
        response = test_client.get(f"/api/artifacts/{artifact_id}", headers=headers)
        assert response.status_code == 200
        
        # Test professor can access student submission artifact (as course instructor)
        prof_token = get_auth_token(test_client, data["professor"])
        prof_headers = {"Authorization": f"Bearer {prof_token}"}
        
        response = test_client.get(f"/api/artifacts/{artifact_id}", headers=prof_headers)
        assert response.status_code == 200
        
        # Test other student cannot access this submission artifact
        with test_db() as session:
            other_student = User(
                id=uuid4(),
                name="Other Student",
                email="other@test.com",
                role=UserRole.student
            )
            session.add(other_student)
            session.commit()
        
        other_token = get_auth_token(test_client, other_student)
        other_headers = {"Authorization": f"Bearer {other_token}"}
        
        response = test_client.get(f"/api/artifacts/{artifact_id}", headers=other_headers)
        assert response.status_code == 403

    def test_submission_timestamps_and_metadata(self, test_client, test_db):
        """Test that submission timestamps and metadata are properly set"""
        data = self.setup_test_assignment(test_db)
        
        token = get_auth_token(test_client, data["student"])
        headers = {"Authorization": f"Bearer {token}"}
        
        files = [("files", ("submission.txt", BytesIO(b"content"), "text/plain"))]
        form_data = {
            "assignment_id": str(data["assignment"].id),
            "submitter_id": str(data["student"].id)
        }
        
        before_submit = datetime.now()
        
        response = test_client.post(
            "/api/submissions/create-with-files",
            data=form_data,
            files=files,
            headers=headers
        )
        
        after_submit = datetime.now()
        
        assert response.status_code == 201
        submission_data = response.json()
        
        # Verify timestamps
        assert "submitted_at" in submission_data
        submitted_at = datetime.fromisoformat(submission_data["submitted_at"].replace('Z', '+00:00'))
        assert before_submit <= submitted_at <= after_submit
        
        # Verify status
        assert submission_data["status"] == "submitted"
        
        # Verify artifact metadata
        artifacts = submission_data["artifacts"]
        for artifact in artifacts:
            assert "created_at" in artifact
            assert "updated_at" in artifact
            assert artifact["status"] == "attached"