from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException

from fair_platform.backend.data.models.artifact import (
    Artifact,
    ArtifactDerivative,
    ArtifactStatus,
    AccessLevel,
)
from fair_platform.backend.data.models.user import User
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.submission import Submission
from fair_platform.backend.data.models.enrollment import Enrollment
from fair_platform.backend.storage.provider import (
    StorageProvider,
    get_storage_provider,
    parse_storage_uri,
)
from fair_platform.backend.core.security.permissions import (
    has_capability,
    has_capability_and_owner,
)


class ArtifactManager:
    """
    Unified interface for artifact lifecycle management.
    
    Handles CRUD operations, state transitions, storage, and permissions.
    All artifact operations should go through this manager to ensure
    consistency and proper error handling.
    """
    
    def __init__(self, db: Session, storage_provider: StorageProvider):
        """
        Initialize ArtifactManager.
        
        Args:
            db: SQLAlchemy database session
            storage_provider: Storage provider implementation
        """
        self.db = db
        self.storage_provider = storage_provider
    
    # ============================================================================
    # CORE CRUD OPERATIONS
    # ============================================================================
    
    def create_artifact(
        self,
        file: UploadFile,
        creator: User,
        title: Optional[str] = None,
        artifact_type: str = "file",
        status: ArtifactStatus = ArtifactStatus.pending,
        access_level: AccessLevel = AccessLevel.private,
        course_id: Optional[UUID] = None,
        assignment_id: Optional[UUID] = None,
        meta: Optional[dict] = None,
    ) -> Artifact:
        """
        Create a new artifact from an uploaded file.
        
        This method handles both file storage and database record creation atomically.
        If database operations fail, the file will be cleaned up automatically.
        
        Args:
            file: The uploaded file
            creator: User creating the artifact
            title: Optional custom title (defaults to filename)
            artifact_type: Type of artifact (default: "file")
            status: Initial status (default: pending)
            access_level: Access control level (default: private)
            course_id: Optional course association
            assignment_id: Optional assignment association
            meta: Optional metadata dictionary
            
        Returns:
            Created Artifact instance
            
        Raises:
            HTTPException: If file has no filename or storage operations fail
        """
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="File must have a filename"
            )

        storage_uri = None
        try:
            artifact_id = uuid4()
            key = self._build_storage_key(artifact_id, "original", file.filename)
            storage_uri = self.storage_provider.put_object(
                key,
                file.file,
                file.content_type or "application/octet-stream",
            )
            
            artifact = Artifact(
                id=artifact_id,
                title=title or file.filename,
                artifact_type=artifact_type,
                creator_id=creator.id,
                status=status,
                access_level=access_level,
                course_id=course_id,
                assignment_id=assignment_id,
                meta=meta,
            )
            
            self.db.add(artifact)
            self.db.flush()
            self.db.add(
                ArtifactDerivative(
                    id=uuid4(),
                    artifact_id=artifact.id,
                    derivative_type="original",
                    storage_uri=storage_uri,
                    mime_type=file.content_type or "application/octet-stream",
                )
            )
            self.db.flush()

            return artifact
        except Exception as e:
            if storage_uri:
                self._delete_derivative_object(storage_uri)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create artifact: {str(e)}"
            )

    def add_derivative(
        self,
        artifact_id: UUID,
        file: UploadFile,
        derivative_type: str,
        user: User,
    ) -> ArtifactDerivative:
        artifact = self.db.get(Artifact, artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        if not self.can_edit(user, artifact):
            raise HTTPException(status_code=403, detail="Permission denied")
        if not file.filename:
            raise HTTPException(status_code=400, detail="File must have a filename")

        key = self._build_storage_key(artifact_id, derivative_type, file.filename)
        storage_uri = self.storage_provider.put_object(
            key,
            file.file,
            file.content_type or "application/octet-stream",
        )
        derivative = ArtifactDerivative(
            id=uuid4(),
            artifact_id=artifact_id,
            derivative_type=derivative_type,
            storage_uri=storage_uri,
            mime_type=file.content_type or "application/octet-stream",
        )
        self.db.add(derivative)
        self.db.flush()
        return derivative
    
    def get_artifact(self, artifact_id: UUID, user: User) -> Artifact:
        """
        Get artifact with permission check.
        
        Args:
            artifact_id: UUID of the artifact
            user: User requesting access
            
        Returns:
            Artifact instance
            
        Raises:
            HTTPException: If artifact not found or access denied
        """
        artifact = self.db.get(Artifact, artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        
        if not self.can_view(user, artifact):
            raise HTTPException(status_code=403, detail="Access denied")
        
        return artifact
    
    def list_artifacts(
        self,
        user: User,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Artifact]:
        """
        List artifacts with optional filters and permission checking.
        
        Args:
            user: User requesting the list
            filters: Optional filters (creator_id, course_id, assignment_id, status, access_level)
            
        Returns:
            List of artifacts the user can view
        """
        query = self.db.query(Artifact)
        
        if filters:
            if "creator_id" in filters:
                query = query.filter(Artifact.creator_id == filters["creator_id"])
            if "course_id" in filters:
                query = query.filter(Artifact.course_id == filters["course_id"])
            if "assignment_id" in filters:
                query = query.filter(Artifact.assignment_id == filters["assignment_id"])
            if "status" in filters:
                query = query.filter(Artifact.status == filters["status"])
            if "access_level" in filters:
                query = query.filter(Artifact.access_level == filters["access_level"])
        
        artifacts = query.all()
        
        return [a for a in artifacts if self.can_view(user, a)]
    
    def update_artifact(
        self,
        artifact_id: UUID,
        user: User,
        title: Optional[str] = None,
        meta: Optional[dict] = None,
        access_level: Optional[AccessLevel] = None,
        status: Optional[ArtifactStatus] = None,
        course_id: Optional[UUID] = None,
        assignment_id: Optional[UUID] = None,
    ) -> Artifact:
        """
        Update artifact metadata with permission check.
        
        Args:
            artifact_id: UUID of artifact to update
            user: User performing the update
            title: New title (optional)
            meta: New metadata (optional)
            access_level: New access level (optional)
            status: New status (optional)
            course_id: New course association (optional)
            assignment_id: New assignment association (optional)
            
        Returns:
            Updated artifact
            
        Raises:
            HTTPException: If artifact not found or access denied
        """
        artifact = self.db.get(Artifact, artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        
        if not self.can_edit(user, artifact):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        if title is not None:
            artifact.title = title
        if meta is not None:
            artifact.meta = meta
        if access_level is not None:
            artifact.access_level = access_level
        if status is not None:
            self._validate_status_transition(artifact.status, status)
            artifact.status = status
        if course_id is not None:
            artifact.course_id = course_id
        if assignment_id is not None:
            artifact.assignment_id = assignment_id
        
        artifact.updated_at = datetime.now()
        self.db.add(artifact)
        self.db.flush()
        
        return artifact

    # TODO: Maybe not the way to go. I don't know how in UI you would let students manage their files, but
    #  you maybe want them to be able to hard delete their own files? Maybe let professors hard delete files
    #  from their courses?
    def delete_artifact(
        self,
        artifact_id: UUID,
        user: User,
        hard_delete: bool = False,
    ) -> None:
        """
        Delete artifact (soft delete by default, hard delete removes file).
        
        Soft delete marks the artifact as archived but preserves the file.
        Hard delete removes both the database record and the physical file.
        Hard delete requires admin privileges.
        
        Args:
            artifact_id: UUID of artifact to delete
            user: User performing deletion
            hard_delete: If True, permanently delete (admin only)
            
        Raises:
            HTTPException: If artifact not found, permission denied, or admin required
        """
        artifact = self.db.get(Artifact, artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        
        if not self.can_delete(user, artifact):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        if hard_delete:
            if not has_capability(user, "cleanup_orphaned_artifacts"):
                raise HTTPException(
                    status_code=403,
                    detail="Hard delete requires admin privileges"
                )
            
            for derivative in list(artifact.derivatives):
                self._delete_derivative_object(derivative.storage_uri)
            
            # Delete from database
            self.db.delete(artifact)
        else:
            # Soft delete - mark as archived
            artifact.status = ArtifactStatus.archived
            artifact.updated_at = datetime.now()
            self.db.add(artifact)
        
        self.db.flush()
    
    # ============================================================================
    # ATOMIC OPERATIONS (Multiple artifacts or complex workflows)
    # ============================================================================
    
    def create_artifacts_bulk(
        self,
        files: List[UploadFile],
        creator: User,
        **kwargs,
    ) -> List[Artifact]:
        """
        Create multiple artifacts atomically.
        
        If any artifact creation fails, all changes are rolled back.
        This prevents orphaned artifacts and partial uploads.
        
        Args:
            files: List of uploaded files
            creator: User creating the artifacts
            **kwargs: Additional arguments passed to create_artifact
            
        Returns:
            List of created artifacts
            
        Raises:
            HTTPException: If any artifact creation fails
        """
        artifacts = []
        
        try:
            for file in files:
                artifact = self.create_artifact(file, creator, **kwargs)
                artifacts.append(artifact)
            return artifacts
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Bulk upload failed: {str(e)}"
            )
    
    def attach_to_assignment(
        self,
        artifact_id: UUID,
        assignment_id: UUID,
        user: User,
    ) -> Artifact:
        """
        Attach existing artifact to an assignment.
        
        Updates the artifact's status to 'attached' and adds the assignment
        relationship. Validates permissions and that the assignment exists.
        
        Args:
            artifact_id: UUID of artifact to attach
            assignment_id: UUID of assignment
            user: User performing the operation
            
        Returns:
            Updated artifact
            
        Raises:
            HTTPException: If artifact/assignment not found or permission denied
        """
        artifact = self.db.get(Artifact, artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        
        if not self.can_edit(user, artifact):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        assignment = self.db.get(Assignment, assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment not in artifact.assignments:
            artifact.assignments.append(assignment)
        
        if artifact.status == ArtifactStatus.pending:
            artifact.status = ArtifactStatus.attached
        
        if artifact.assignment_id is None or artifact.assignment_id != assignment_id:
            artifact.assignment_id = assignment_id
        
        if artifact.course_id is None or artifact.course_id != assignment.course_id:
            artifact.course_id = assignment.course_id
        
        artifact.updated_at = datetime.now()
        self.db.add(artifact)
        self.db.flush()
        
        return artifact
    
    def attach_to_submission(
        self,
        artifact_id: UUID,
        submission_id: UUID,
        user: User,
    ) -> Artifact:
        """
        Attach existing artifact to a submission.
        
        Updates the artifact's status to 'attached' and adds the submission
        relationship. Validates permissions and that the submission exists.
        
        Args:
            artifact_id: UUID of artifact to attach
            submission_id: UUID of submission
            user: User performing the operation
            
        Returns:
            Updated artifact
            
        Raises:
            HTTPException: If artifact/submission not found or permission denied
        """
        artifact = self.db.get(Artifact, artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        
        if not self.can_edit(user, artifact):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        submission = self.db.get(Submission, submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        if submission not in artifact.submissions:
            artifact.submissions.append(submission)
        
        if artifact.status == ArtifactStatus.pending:
            artifact.status = ArtifactStatus.attached
        
        if artifact.assignment_id is None and submission.assignment_id is not None:
            artifact.assignment_id = submission.assignment_id

        if artifact.course_id is None and submission.assignment is not None:
            artifact.course_id = submission.assignment.course_id
        
        artifact.updated_at = datetime.now()
        self.db.add(artifact)
        self.db.flush()
        
        return artifact
    
    def detach_from_assignment(
        self,
        artifact_id: UUID,
        assignment_id: UUID,
        user: User,
    ) -> Artifact:
        """
        Detach artifact from assignment, mark as orphaned if no other attachments.
        
        Args:
            artifact_id: UUID of artifact to detach
            assignment_id: UUID of assignment
            user: User performing the operation
            
        Returns:
            Updated artifact
            
        Raises:
            HTTPException: If artifact/assignment not found or permission denied
        """
        artifact = self.db.get(Artifact, artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        
        if not self.can_edit(user, artifact):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        assignment = self.db.get(Assignment, assignment_id)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        if assignment in artifact.assignments:
            # TODO: The table assignment_artifacts should also be aware of this change?
            artifact.assignments.remove(assignment)
        
        if not artifact.assignments and not artifact.submissions:
            artifact.status = ArtifactStatus.orphaned
        
        artifact.updated_at = datetime.now()
        self.db.add(artifact)
        self.db.flush()
        
        return artifact
    
    def detach_from_submission(
        self,
        artifact_id: UUID,
        submission_id: UUID,
        user: User,
    ) -> Artifact:
        """
        Detach artifact from submission, mark as orphaned if no other attachments.
        
        Args:
            artifact_id: UUID of artifact to detach
            submission_id: UUID of submission
            user: User performing the operation
            
        Returns:
            Updated artifact
            
        Raises:
            HTTPException: If artifact/submission not found or permission denied
        """
        artifact = self.db.get(Artifact, artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        
        if not self.can_edit(user, artifact):
            raise HTTPException(status_code=403, detail="Permission denied")
        
        submission = self.db.get(Submission, submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")
        
        if submission in artifact.submissions:
            # TODO: The table submission_artifacts should also be aware of this change
            artifact.submissions.remove(submission)

        if not artifact.assignments and not artifact.submissions:
            artifact.status = ArtifactStatus.orphaned
        
        artifact.updated_at = datetime.now()
        self.db.add(artifact)
        self.db.flush()
        
        return artifact
    
    # ============================================================================
    # LIFECYCLE MANAGEMENT
    # ============================================================================
    
    def mark_orphaned(self, artifact_id: UUID) -> None:
        """
        Mark artifact as orphaned (called by event listeners).
        
        This is typically called automatically by SQLAlchemy event listeners
        when parent entities are deleted.
        
        Args:
            artifact_id: UUID of artifact to mark as orphaned
        """
        artifact = self.db.get(Artifact, artifact_id)
        if artifact:
            artifact.status = ArtifactStatus.orphaned
            artifact.updated_at = datetime.now()
            self.db.add(artifact)
    
    def cleanup_orphaned(
        self,
        older_than_days: int = 7,
        hard_delete: bool = False,
    ) -> int:
        """
        Cleanup orphaned artifacts older than specified days.
        
        This administrative function removes orphaned artifacts that have been
        in the orphaned state for longer than the specified period.
        
        Args:
            older_than_days: Only cleanup artifacts orphaned for this many days
            hard_delete: If True, permanently delete files (admin only)
            
        Returns:
            Number of artifacts cleaned up
        """
        cutoff = datetime.now() - timedelta(days=older_than_days)
        orphaned_artifacts = self.db.query(Artifact).filter(
            Artifact.status == ArtifactStatus.orphaned,
            Artifact.updated_at < cutoff
        ).all()
        
        count = 0
        for artifact in orphaned_artifacts:
            if hard_delete:
                for derivative in list(artifact.derivatives):
                    self._delete_derivative_object(derivative.storage_uri)
                self.db.delete(artifact)
            else:
                artifact.status = ArtifactStatus.archived
                artifact.updated_at = datetime.now()
                self.db.add(artifact)
            count += 1
        
        self.db.flush()
        return count
    
    # ============================================================================
    # PERMISSION SYSTEM
    # ============================================================================
    
    def can_view(self, user: User, artifact: Artifact) -> bool:
        """
        Check if user can view artifact.
        
        Permission rules:
        - Admins can view everything
        - Creators can view their own artifacts
        - Course instructors can view course artifacts
        - Students can view their own submission artifacts
        - Public artifacts can be viewed by anyone
        - Course-level artifacts can be viewed by course members (future enhancement)
        
        Args:
            user: User requesting access
            artifact: Artifact to check
            
        Returns:
            True if user can view, False otherwise
        """
        # Admins can view everything
        if has_capability(user, "view_all_artifacts"):
            return True
        
        # Creator can always view their own artifacts
        if artifact.creator_id == user.id:
            return True
        
        # Public artifacts are visible to everyone
        if artifact.access_level == AccessLevel.public:
            return True
        
        # Course instructors can view course-level artifacts
        if artifact.course_id and has_capability(user, "manage_artifact"):
            course = self.db.get(Course, artifact.course_id)
            if course and has_capability_and_owner(user, "manage_artifact", course.instructor_id):
                return True
        
        # Students can view artifacts from their own submissions
        if artifact.submissions:
            for submission in artifact.submissions:
                if submission.submitter_id == user.id:
                    return True

        # Enrolled users can view course and assignment scoped artifacts.
        if artifact.access_level in [AccessLevel.course, AccessLevel.assignment] and artifact.course_id:
            enrollment = self.db.query(Enrollment).filter(
                Enrollment.user_id == user.id,
                Enrollment.course_id == artifact.course_id,
            ).first()
            if enrollment:
                return True

        return False
    
    def can_edit(self, user: User, artifact: Artifact) -> bool:
        """
        Check if user can edit artifact.
        
        Permission rules:
        - Admins can edit everything
        - Creators can edit their own artifacts

        Args:
            user: User requesting access
            artifact: Artifact to check
            
        Returns:
            True if user can edit, False otherwise
        """
        if has_capability(user, "manage_users"):
            return True
        
        if artifact.creator_id == user.id:
            return True

        if artifact.course_id and has_capability(user, "manage_artifact"):
            course = self.db.get(Course, artifact.course_id)
            if course and has_capability_and_owner(user, "manage_artifact", course.instructor_id):
                valid_levels = [AccessLevel.course, AccessLevel.assignment, AccessLevel.public]
                if artifact.access_level in valid_levels:
                    return True
        
        return False
    
    def can_delete(self, user: User, artifact: Artifact) -> bool:
        """
        Check if user can delete artifact.
        
        Permission rules:
        - Admins can delete everything
        - Creators can delete their own artifacts
        - Course instructors can delete course/assignment/public artifacts from their courses
        
        Args:
            user: User requesting access
            artifact: Artifact to check
            
        Returns:
            True if user can delete, False otherwise
        """
        # Admins can delete everything
        if has_capability(user, "manage_users"):
            return True
        
        # Creator can delete their own artifacts
        if artifact.creator_id == user.id:
            return True
        
        # Course instructors can delete certain artifacts from their courses
        if artifact.course_id and has_capability(user, "manage_artifact"):
            course = self.db.get(Course, artifact.course_id)
            if course and has_capability_and_owner(user, "manage_artifact", course.instructor_id):
                # Can delete course, assignment, and public artifacts
                valid_levels = [AccessLevel.course, AccessLevel.assignment, AccessLevel.public]
                if artifact.access_level in valid_levels:
                    return True
        
        return False
    
    # ============================================================================
    # STORAGE OPERATIONS (Private)
    # ============================================================================
    
    def _build_storage_key(self, artifact_id: UUID, derivative_type: str, filename: str) -> str:
        safe_name = Path(filename).name
        return f"artifacts/{artifact_id}/{derivative_type}_{safe_name}"

    def _delete_derivative_object(self, storage_uri: str) -> None:
        _, key = parse_storage_uri(storage_uri)
        self.storage_provider.delete_object(key)
    
    def _validate_status_transition(self, current: ArtifactStatus, new: ArtifactStatus) -> None:
        """
        Validate that a status transition is allowed.
        
        Valid transitions:
        - pending → attached, archived
        - attached → orphaned, archived
        - orphaned → archived, attached (re-attachment)
        - archived → attached (restoration)
        
        Args:
            current: Current status
            new: New status to transition to
            
        Raises:
            HTTPException: If transition is invalid
        """
        valid_transitions = {
            ArtifactStatus.pending: [ArtifactStatus.attached, ArtifactStatus.archived],
            ArtifactStatus.attached: [ArtifactStatus.orphaned, ArtifactStatus.archived],
            ArtifactStatus.orphaned: [ArtifactStatus.archived, ArtifactStatus.attached],
            ArtifactStatus.archived: [ArtifactStatus.attached],
        }
        
        if current not in valid_transitions or new not in valid_transitions[current]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status transition from {current} to {new}"
            )


def get_artifact_manager(db: Session) -> ArtifactManager:
    """
    Factory function to get ArtifactManager instance.
    
    Args:
        db: SQLAlchemy database session
        
    Returns:
        ArtifactManager instance
    """
    return ArtifactManager(db, storage_provider=get_storage_provider())


__all__ = ["ArtifactManager", "get_artifact_manager"]
