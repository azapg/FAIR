"""
Tests for artifacts API access control and permissions.

These tests enforce the ownership and permission system proposed in 
ARTIFACTS_API_IMPLEMENTATION.md, testing various scenarios of who can
access, edit, and delete artifacts based on roles and relationships.
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from io import BytesIO
from fastapi.testclient import TestClient

from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.data.models.course import Course  
from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.artifact import Artifact
from fair_platform.backend.data.models.submission import Submission
from tests.conftest import get_auth_token


class TestArtifactAPIPermissions:
    """Test access control for artifact operations"""
    
    def setup_test_data(self, test_db):
        """Create test users, courses, and artifacts for permission testing"""
        with test_db() as session:
            # Create users with different roles
            prof1_id = uuid4()
            prof1 = User(
                id=prof1_id,
                name="Professor One",
                email="prof1@test.com",
                role=UserRole.professor
            )
            
            prof2_id = uuid4() 
            prof2 = User(
                id=prof2_id,
                name="Professor Two", 
                email="prof2@test.com",
                role=UserRole.professor
            )
            
            student1_id = uuid4()
            student1 = User(
                id=student1_id,
                name="Student One",
                email="student1@test.com", 
                role=UserRole.student
            )
            
            student2_id = uuid4()
            student2 = User(
                id=student2_id,
                name="Student Two",
                email="student2@test.com",
                role=UserRole.student
            )
            
            admin_id = uuid4()
            admin = User(
                id=admin_id,
                name="Admin User",
                email="admin@test.com",
                role=UserRole.admin
            )
            
            session.add_all([prof1, prof2, student1, student2, admin])
            
            # Create courses
            course1_id = uuid4()
            course1 = Course(
                id=course1_id,
                name="Course One",
                description="Course taught by Prof1",
                instructor_id=prof1_id
            )
            
            course2_id = uuid4()
            course2 = Course(
                id=course2_id,
                name="Course Two", 
                description="Course taught by Prof2",
                instructor_id=prof2_id
            )
            
            session.add_all([course1, course2])
            
            # Create assignment in course1
            assignment1_id = uuid4()
            assignment1 = Assignment(
                id=assignment1_id,
                course_id=course1_id,
                title="Assignment One",
                description="Assignment in course1",
                deadline=datetime.now() + timedelta(days=7),
                max_grade={"points": 100}
            )
            
            session.add(assignment1)
            session.commit()
            
            # Create artifacts with different access levels and ownership
            artifacts = [
                # Private artifact owned by prof1
                Artifact(
                    id=uuid4(),
                    title="Prof1 Private Document",
                    artifact_type="document",
                    mime="application/pdf",
                    storage_path="/path/prof1_private.pdf",
                    storage_type="local",
                    creator_id=prof1_id,
                    status="attached",
                    access_level="private"
                ),
                
                # Course-level artifact in course1 (prof1's course)
                Artifact(
                    id=uuid4(),
                    title="Course1 Material",
                    artifact_type="document", 
                    mime="application/pdf",
                    storage_path="/path/course1_material.pdf",
                    storage_type="local",
                    creator_id=prof1_id,
                    course_id=course1_id,
                    status="attached",
                    access_level="course"
                ),
                
                # Assignment-level artifact
                Artifact(
                    id=uuid4(),
                    title="Assignment1 Instructions",
                    artifact_type="document",
                    mime="application/pdf", 
                    storage_path="/path/assignment1_instructions.pdf",
                    storage_type="local",
                    creator_id=prof1_id,
                    course_id=course1_id,
                    assignment_id=assignment1_id,
                    status="attached",
                    access_level="assignment"
                ),
                
                # Public artifact
                Artifact(
                    id=uuid4(),
                    title="Public Document",
                    artifact_type="document",
                    mime="application/pdf",
                    storage_path="/path/public.pdf",
                    storage_type="local",
                    creator_id=prof1_id,
                    status="attached", 
                    access_level="public"
                ),
                
                # Student-created artifact
                Artifact(
                    id=uuid4(),
                    title="Student1 Submission",
                    artifact_type="document",
                    mime="application/pdf",
                    storage_path="/path/student1_submission.pdf",
                    storage_type="local",
                    creator_id=student1_id,
                    course_id=course1_id,
                    assignment_id=assignment1_id,
                    status="attached",
                    access_level="assignment"
                )
            ]
            
            session.add_all(artifacts)
            session.commit()
            
            return {
                "prof1": prof1, "prof2": prof2, 
                "student1": student1, "student2": student2, "admin": admin,
                "course1": course1, "course2": course2,
                "assignment1": assignment1,
                "artifacts": artifacts
            }

    def test_artifact_list_permission_filtering(self, test_client, test_db):
        """Test that artifact listing respects permission filtering"""
        data = self.setup_test_data(test_db)
        
        # Test professor1 can see their artifacts + course/assignment artifacts
        token = get_auth_token(test_client, data["prof1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.get("/api/artifacts", headers=headers)
        assert response.status_code == 200
        
        artifacts = response.json()
        accessible_titles = [a["title"] for a in artifacts]
        
        # Prof1 should see: private + course1 + assignment1 + public + student submission (as instructor)
        expected_titles = [
            "Prof1 Private Document",
            "Course1 Material", 
            "Assignment1 Instructions",
            "Public Document",
            "Student1 Submission"
        ]
        
        for title in expected_titles:
            assert title in accessible_titles
            
        # Test student1 permissions
        token = get_auth_token(test_client, data["student1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.get("/api/artifacts", headers=headers)
        assert response.status_code == 200
        
        artifacts = response.json()
        accessible_titles = [a["title"] for a in artifacts]
        
        # Student1 should see: their own submission + assignment1 instructions + public
        expected_titles = [
            "Assignment1 Instructions",  # Assignment-level in course they're enrolled in
            "Public Document",
            "Student1 Submission"  # Their own artifact
        ]
        
        for title in expected_titles:
            assert title in accessible_titles
            
        # Should NOT see private or course materials
        assert "Prof1 Private Document" not in accessible_titles
        assert "Course1 Material" not in accessible_titles

    def test_artifact_get_individual_permissions(self, test_client, test_db):
        """Test individual artifact access permissions"""
        data = self.setup_test_data(test_db)
        private_artifact = data["artifacts"][0]  # Prof1 private
        course_artifact = data["artifacts"][1]   # Course1 material
        public_artifact = data["artifacts"][3]   # Public document
        
        # Test owner can access private artifact
        token = get_auth_token(test_client, data["prof1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.get(f"/api/artifacts/{private_artifact.id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Prof1 Private Document"
        
        # Test non-owner cannot access private artifact
        token = get_auth_token(test_client, data["student1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.get(f"/api/artifacts/{private_artifact.id}", headers=headers)
        assert response.status_code == 403
        
        # Test anyone can access public artifact
        response = test_client.get(f"/api/artifacts/{public_artifact.id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Public Document"
        
        # Test course instructor can access course artifact
        token = get_auth_token(test_client, data["prof1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.get(f"/api/artifacts/{course_artifact.id}", headers=headers)
        assert response.status_code == 200
        
        # Test non-course instructor cannot access course artifact
        token = get_auth_token(test_client, data["prof2"])
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.get(f"/api/artifacts/{course_artifact.id}", headers=headers)
        assert response.status_code == 403

    def test_artifact_edit_permissions(self, test_client, test_db):
        """Test artifact edit permissions"""
        data = self.setup_test_data(test_db)
        private_artifact = data["artifacts"][0]  # Prof1 private
        student_artifact = data["artifacts"][4]  # Student1 submission
        
        # Test owner can edit their artifact
        token = get_auth_token(test_client, data["prof1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        update_data = {
            "title": "Updated Private Document",
            "meta": {"updated": True}
        }
        
        response = test_client.put(
            f"/api/artifacts/{private_artifact.id}",
            json=update_data,
            headers=headers
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Private Document"
        
        # Test non-owner cannot edit artifact
        token = get_auth_token(test_client, data["student1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        update_data = {"title": "Hacked Document"}
        
        response = test_client.put(
            f"/api/artifacts/{private_artifact.id}",
            json=update_data,
            headers=headers
        )
        assert response.status_code == 403
        
        # Test course instructor can edit course artifacts
        course_artifact = data["artifacts"][1]  # Course1 material
        token = get_auth_token(test_client, data["prof1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        update_data = {"title": "Updated Course Material"}
        
        response = test_client.put(
            f"/api/artifacts/{course_artifact.id}",
            json=update_data,
            headers=headers
        )
        assert response.status_code == 200
        
        # Test student can edit their own submission artifact
        token = get_auth_token(test_client, data["student1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        update_data = {"title": "Updated Student Submission"}
        
        response = test_client.put(
            f"/api/artifacts/{student_artifact.id}",
            json=update_data,
            headers=headers
        )
        assert response.status_code == 200

    def test_artifact_delete_permissions(self, test_client, test_db):
        """Test artifact deletion permissions"""
        data = self.setup_test_data(test_db)
        
        # Create a disposable artifact for testing deletion
        with test_db() as session:
            disposable_artifact = Artifact(
                id=uuid4(),
                title="Disposable Document",
                artifact_type="document",
                mime="application/pdf",
                storage_path="/path/disposable.pdf",
                storage_type="local",
                creator_id=data["prof1"].id,
                status="attached",
                access_level="private"
            )
            session.add(disposable_artifact)
            session.commit()
            artifact_id = disposable_artifact.id
        
        # Test owner can delete their artifact
        token = get_auth_token(test_client, data["prof1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.delete(f"/api/artifacts/{artifact_id}", headers=headers)
        assert response.status_code == 204
        
        # Verify artifact was deleted/marked for deletion
        response = test_client.get(f"/api/artifacts/{artifact_id}", headers=headers)
        assert response.status_code == 404

    def test_artifact_delete_protection_active_submissions(self, test_client, test_db):
        """Test that artifacts attached to active submissions cannot be deleted by non-owners"""
        data = self.setup_test_data(test_db)
        
        # Create submission that uses an artifact
        with test_db() as session:
            submission = Submission(
                id=uuid4(),
                assignment_id=data["assignment1"].id,
                submitter_id=data["student1"].id,
                status="submitted",  # Active submission
                submitted_at=datetime.now()
            )
            session.add(submission)
            
            # Link artifact to submission
            student_artifact = data["artifacts"][4]  # Student1 submission artifact
            submission.artifacts.append(student_artifact)
            session.commit()
        
        # Test course instructor cannot delete student artifact attached to active submission
        token = get_auth_token(test_client, data["prof1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.delete(f"/api/artifacts/{student_artifact.id}", headers=headers)
        assert response.status_code == 403  # Or 409 for conflict
        
        # But student (owner) should still be able to delete their own
        token = get_auth_token(test_client, data["student1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.delete(f"/api/artifacts/{student_artifact.id}", headers=headers)
        assert response.status_code == 204

    def test_admin_override_permissions(self, test_client, test_db):
        """Test that admin users can override normal permission restrictions"""
        data = self.setup_test_data(test_db)
        private_artifact = data["artifacts"][0]  # Prof1 private
        
        # Test admin can access any artifact
        token = get_auth_token(test_client, data["admin"])
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.get(f"/api/artifacts/{private_artifact.id}", headers=headers)
        assert response.status_code == 200
        
        # Test admin can edit any artifact
        update_data = {"title": "Admin Updated Document"}
        
        response = test_client.put(
            f"/api/artifacts/{private_artifact.id}",
            json=update_data,
            headers=headers
        )
        assert response.status_code == 200
        
        # Test admin can delete any artifact
        response = test_client.delete(f"/api/artifacts/{private_artifact.id}", headers=headers)
        assert response.status_code == 204

    def test_course_context_filtering(self, test_client, test_db):
        """Test filtering artifacts by course context"""
        data = self.setup_test_data(test_db)
        
        # Test course instructor can filter by their course
        token = get_auth_token(test_client, data["prof1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.get(
            f"/api/artifacts?course_id={data['course1'].id}",
            headers=headers
        )
        assert response.status_code == 200
        
        artifacts = response.json()
        # Should only return artifacts from course1
        for artifact in artifacts:
            if artifact.get("course_id"):
                assert artifact["course_id"] == str(data["course1"].id)
        
        # Test instructor cannot filter by course they don't own
        response = test_client.get(
            f"/api/artifacts?course_id={data['course2'].id}",
            headers=headers
        )
        # Should return empty or 403
        assert response.status_code in [200, 403]
        if response.status_code == 200:
            assert len(response.json()) == 0

    def test_assignment_context_filtering(self, test_client, test_db):
        """Test filtering artifacts by assignment context"""  
        data = self.setup_test_data(test_db)
        
        # Test course instructor can filter by assignment
        token = get_auth_token(test_client, data["prof1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.get(
            f"/api/artifacts?assignment_id={data['assignment1'].id}",
            headers=headers
        )
        assert response.status_code == 200
        
        artifacts = response.json()
        # Should only return artifacts from assignment1
        for artifact in artifacts:
            if artifact.get("assignment_id"):
                assert artifact["assignment_id"] == str(data["assignment1"].id)

    def test_artifact_download_permissions(self, test_client, test_db):
        """Test file download permissions"""
        data = self.setup_test_data(test_db)
        private_artifact = data["artifacts"][0]  # Prof1 private
        public_artifact = data["artifacts"][3]   # Public document
        
        # Test owner can download private artifact
        token = get_auth_token(test_client, data["prof1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.get(f"/api/artifacts/{private_artifact.id}/download", headers=headers)
        # May be 200 (file content) or 302 (redirect to signed URL)
        assert response.status_code in [200, 302]
        
        # Test non-owner cannot download private artifact
        token = get_auth_token(test_client, data["student1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        response = test_client.get(f"/api/artifacts/{private_artifact.id}/download", headers=headers)
        assert response.status_code == 403
        
        # Test anyone can download public artifact
        response = test_client.get(f"/api/artifacts/{public_artifact.id}/download", headers=headers)
        assert response.status_code in [200, 302]

    def test_unauthenticated_access_restrictions(self, test_client, test_db):
        """Test that unauthenticated users can only access public artifacts"""
        data = self.setup_test_data(test_db)
        
        # Test unauthenticated access to artifact list
        response = test_client.get("/api/artifacts")
        assert response.status_code == 401  # Unauthorized
        
        # Test unauthenticated access to specific artifacts
        private_artifact = data["artifacts"][0]
        response = test_client.get(f"/api/artifacts/{private_artifact.id}")
        assert response.status_code == 401
        
        # Public artifacts might be accessible without auth (depending on design)
        public_artifact = data["artifacts"][3]
        response = test_client.get(f"/api/artifacts/{public_artifact.id}")
        # Could be 401 (if auth required) or 200 (if public access allowed)
        assert response.status_code in [200, 401]

    def test_permission_computed_fields(self, test_client, test_db):
        """Test that artifact responses include computed permission fields"""
        data = self.setup_test_data(test_db)
        
        # Test owner sees full permissions
        token = get_auth_token(test_client, data["prof1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        private_artifact = data["artifacts"][0]
        response = test_client.get(f"/api/artifacts/{private_artifact.id}", headers=headers)
        assert response.status_code == 200
        
        artifact_data = response.json()
        # Should include computed permission fields
        assert "can_view" in artifact_data
        assert "can_edit" in artifact_data 
        assert "can_delete" in artifact_data
        assert artifact_data["can_view"] is True
        assert artifact_data["can_edit"] is True
        assert artifact_data["can_delete"] is True
        
        # Test non-owner sees restricted permissions
        token = get_auth_token(test_client, data["student1"])
        headers = {"Authorization": f"Bearer {token}"}
        
        public_artifact = data["artifacts"][3]
        response = test_client.get(f"/api/artifacts/{public_artifact.id}", headers=headers)
        assert response.status_code == 200
        
        artifact_data = response.json()
        assert artifact_data["can_view"] is True
        assert artifact_data["can_edit"] is False
        assert artifact_data["can_delete"] is False