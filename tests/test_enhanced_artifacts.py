import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.artifact import Artifact


class TestEnhancedArtifactModel:
    """Test the enhanced artifact model with ownership and lifecycle management"""
    
    def test_artifact_creation_requires_creator(self, test_db):
        """Test that artifacts must have a creator_id"""
        with test_db() as session:
            user = User(
                id=uuid4(),
                name="Test User",
                email="user@test.com",
                role=UserRole.student
            )
            session.add(user)
            session.commit()
            
            # Artifact creation should require creator_id
            artifact = Artifact(
                id=uuid4(),
                title="Test Document",
                artifact_type="document",
                mime="application/pdf",
                storage_path="/path/to/file.pdf",
                storage_type="local",
            )
            session.add(artifact)
            
            with pytest.raises(IntegrityError):
                session.commit()
    
    def test_artifact_with_valid_creator(self, test_db):
        """Test artifact creation with valid creator"""
        with test_db() as session:
            user_id = uuid4()
            user = User(
                id=user_id,
                name="Test User", 
                email="user@test.com",
                role=UserRole.student
            )
            session.add(user)
            session.commit()
            
            artifact_id = uuid4()
            artifact = Artifact(
                id=artifact_id,
                title="Test Document",
                artifact_type="document", 
                mime="application/pdf",
                storage_path="/path/to/file.pdf",
                storage_type="local",
                creator_id=user_id,
                status="pending",
                access_level="private"
            )
            session.add(artifact)
            session.commit()
            session.refresh(artifact)            

            assert artifact.creator_id == user_id
            assert artifact.creator.email == "user@test.com"
            assert artifact.status == "pending"
            assert artifact.access_level == "private"
            assert artifact.created_at is not None
            assert artifact.updated_at is not None

    def test_artifact_course_context_relationship(self, test_db):
        """Test artifact can be associated with a course"""
        with test_db() as session:
            prof_id = uuid4()
            professor = User(
                id=prof_id,
                name="Prof Smith",
                email="prof@test.com", 
                role=UserRole.professor
            )
            session.add(professor)
            
            course_id = uuid4()
            course = Course(
                id=course_id,
                name="Test Course",
                description="Test course description",
                instructor_id=prof_id
            )
            session.add(course)
            session.commit()
            
            artifact = Artifact(
                id=uuid4(),
                title="Course Material",
                artifact_type="document",
                mime="application/pdf", 
                storage_path="/path/to/course_material.pdf",
                storage_type="local",
                creator_id=prof_id,
                course_id=course_id,
                status="attached",
                access_level="course"
            )
            session.add(artifact)
            session.commit()
            session.refresh(artifact)
            
            assert artifact.course_id == course_id
            assert artifact.course.name == "Test Course"
            assert artifact.access_level == "course"

    def test_artifact_assignment_context_relationship(self, test_db):
        """Test artifact can be associated with an assignment"""
        with test_db() as session:
            prof_id = uuid4()
            professor = User(
                id=prof_id,
                name="Prof Smith",
                email="prof@test.com",
                role=UserRole.professor
            )
            session.add(professor)
            
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
                title="Test Assignment",
                description="Test assignment description",
                deadline=datetime.now() + timedelta(days=7),
                max_grade={"points": 100}
            )
            session.add(assignment)
            session.commit()
            
            artifact = Artifact(
                id=uuid4(),
                title="Assignment Instructions",
                artifact_type="document",
                mime="application/pdf",
                storage_path="/path/to/instructions.pdf", 
                storage_type="local",
                creator_id=prof_id,
                course_id=course_id,
                assignment_id=assignment_id,
                status="attached",
                access_level="assignment"
            )
            session.add(artifact)
            session.commit()
            session.refresh(artifact)
            
            assert artifact.assignment_id == assignment_id
            assert artifact.course_id == course_id
            assert artifact.creator_id == prof_id
            assert artifact.assignment.title == "Test Assignment"
            assert artifact.course.name == "Test Course"

    def test_artifact_status_enum_validation(self, test_db):
        """Test that artifact status follows expected enum values"""
        with test_db() as session:
            user = User(
                id=uuid4(),
                name="Test User",
                email="user@test.com",
                role=UserRole.student
            )
            session.add(user)
            session.commit()
            
            valid_statuses = ["pending", "attached", "orphaned", "archived", "deleted"]
            
            for status in valid_statuses:
                artifact = Artifact(
                    id=uuid4(),
                    title=f"Test Document {status}",
                    artifact_type="document",
                    mime="application/pdf",
                    storage_path=f"/path/to/file_{status}.pdf",
                    storage_type="local",
                    creator_id=user.id,
                    status=status,
                    access_level="private"
                )
                session.add(artifact)
                session.commit()
                session.refresh(artifact)
                assert artifact.status == status

    def test_artifact_access_level_validation(self, test_db):
        """Test that access level follows expected enum values"""
        with test_db() as session:
            user = User(
                id=uuid4(),
                name="Test User", 
                email="user@test.com",
                role=UserRole.student
            )
            session.add(user)
            session.commit()
            
            valid_access_levels = ["private", "course", "assignment", "public"]
            
            for access_level in valid_access_levels:
                artifact = Artifact(
                    id=uuid4(),
                    title=f"Test Document {access_level}",
                    artifact_type="document",
                    mime="application/pdf", 
                    storage_path=f"/path/to/file_{access_level}.pdf",
                    storage_type="local",
                    creator_id=user.id,
                    status="pending",
                    access_level=access_level
                )
                session.add(artifact)
                session.commit()
                session.refresh(artifact)
                assert artifact.access_level == access_level

    def test_artifact_timestamps_auto_management(self, test_db):
        """Test that created_at and updated_at are managed automatically"""
        with test_db() as session:
            user = User(
                id=uuid4(),
                name="Test User",
                email="user@test.com", 
                role=UserRole.student
            )
            session.add(user)
            session.commit()
            
            artifact = Artifact(
                id=uuid4(),
                title="Test Document",
                artifact_type="document",
                mime="application/pdf",
                storage_path="/path/to/file.pdf", 
                storage_type="local",
                creator_id=user.id,
                status="pending",
                access_level="private"
            )
            session.add(artifact)
            session.commit()
            session.refresh(artifact)
            
            created_at = artifact.created_at
            updated_at = artifact.updated_at
            
            assert created_at is not None
            assert updated_at is not None
            assert created_at == updated_at  # Should be same at creation
            
            artifact.title = "Updated Document"
            session.commit()
            session.refresh(artifact)
            
            assert artifact.created_at == created_at
            assert artifact.updated_at > updated_at

    def test_artifact_foreign_key_constraints(self, test_db):
        """Test that foreign key constraints are enforced"""
        with test_db() as session:
            with pytest.raises(IntegrityError):
                artifact = Artifact(
                    id=uuid4(),
                    title="Test Document",
                    artifact_type="document", 
                    mime="application/pdf",
                    storage_path="/path/to/file.pdf",
                    storage_type="local",
                    creator_id=uuid4(),  # Non-existent user
                    status="pending",
                    access_level="private"
                )
                session.add(artifact)
                session.commit()

    def test_artifact_deletion_cascade_behavior(self, test_db):
        """Test how artifact deletion affects relationships"""
        with test_db() as session:
            prof_id = uuid4()
            professor = User(
                id=prof_id,
                name="Prof Smith",
                email="prof@test.com",
                role=UserRole.professor
            )
            session.add(professor)
            
            course_id = uuid4()
            course = Course(
                id=course_id,
                name="Test Course", 
                description="Test course",
                instructor_id=prof_id
            )
            session.add(course)
            session.commit()
            
            artifact = Artifact(
                id=uuid4(),
                title="Course Material",
                artifact_type="document",
                mime="application/pdf",
                storage_path="/path/to/material.pdf",
                storage_type="local", 
                creator_id=prof_id,
                course_id=course_id,
                status="attached",
                access_level="course"
            )
            session.add(artifact)
            session.commit()
            
            artifact_id = artifact.id
            
            session.delete(course)
            session.commit()
            
            remaining_artifact = session.get(Artifact, artifact_id)
            assert remaining_artifact is not None