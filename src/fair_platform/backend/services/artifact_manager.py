from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException

from fair_platform.backend.data.models.artifact import Artifact, ArtifactStatus, AccessLevel
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.submission import Submission
from fair_platform.backend.data.storage import storage


class ArtifactManager:
    """
    Unified interface for artifact lifecycle management.
    
    Handles CRUD operations, state transitions, storage, and permissions.
    All artifact operations should go through this manager to ensure
    consistency and proper error handling.
    """
    
    def __init__(self, db: Session, storage_backend=None):
        """
        Initialize ArtifactManager.
        
        Args:
            db: SQLAlchemy database session
            storage_backend: Optional storage backend for testing (defaults to platform storage)
        """
        self.db = db
        self.storage = storage_backend or storage
    
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

        storage_path = None
        try:
            artifact_id = uuid4()
            storage_path = self._store_file(artifact_id, file)
            
            artifact = Artifact(
                id=artifact_id,
                title=title or file.filename,
                artifact_type=artifact_type,
                mime=file.content_type or "application/octet-stream",
                storage_path=storage_path,
                storage_type="local",
                creator_id=creator.id,
                status=status,
                access_level=access_level,
                course_id=course_id,
                assignment_id=assignment_id,
                meta=meta,
            )
            
            self.db.add(artifact)
            self.db.flush()

            return artifact
        except Exception as e:
            if storage_path:
                self._delete_file(storage_path)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create artifact: {str(e)}"
            )
    
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
            if user.role != UserRole.admin:
                raise HTTPException(
                    status_code=403,
                    detail="Hard delete requires admin privileges"
                )
            
            # Delete physical file
            self._delete_file(artifact.storage_path)
            
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
                self._delete_file(artifact.storage_path)
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
        if user.role == UserRole.admin:
            return True
        
        # Creator can always view their own artifacts
        if artifact.creator_id == user.id:
            return True
        
        # Public artifacts are visible to everyone
        if artifact.access_level == AccessLevel.public:
            return True
        
        # Course instructors can view course-level artifacts
        if artifact.course_id and user.role == UserRole.professor:
            course = self.db.get(Course, artifact.course_id)
            if course and course.instructor_id == user.id:
                return True
        
        # Students can view artifacts from their own submissions
        if artifact.submissions:
            for submission in artifact.submissions:
                if submission.submitter_id == user.id:
                    return True
        
        # Course and assignment level artifacts
        # TODO: Add enrollment check when enrollment system is implemented
        if artifact.access_level in [AccessLevel.course, AccessLevel.assignment]:
            # For now, allow access if the user is a student
            # This will be refined with proper enrollment checking
            if user.role == UserRole.student:
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
        if user.role == UserRole.admin:
            return True
        
        if artifact.creator_id == user.id:
            return True

        if artifact.course_id and user.role == UserRole.professor:
            course = self.db.get(Course, artifact.course_id)
            if course and course.instructor_id == user.id:
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
        if user.role == UserRole.admin:
            return True
        
        # Creator can delete their own artifacts
        if artifact.creator_id == user.id:
            return True
        
        # Course instructors can delete certain artifacts from their courses
        if artifact.course_id and user.role == UserRole.professor:
            course = self.db.get(Course, artifact.course_id)
            if course and course.instructor_id == user.id:
                # Can delete course, assignment, and public artifacts
                valid_levels = [AccessLevel.course, AccessLevel.assignment, AccessLevel.public]
                if artifact.access_level in valid_levels:
                    return True
        
        return False
    
    # ============================================================================
    # STORAGE OPERATIONS (Private)
    # ============================================================================
    
    def _store_file(self, artifact_id: UUID, file: UploadFile) -> str:
        """
        Store file physically and return storage path.
        
        Args:
            artifact_id: UUID for the artifact
            file: Uploaded file
            
        Returns:
            Storage path string
        """
        if not file.filename:
            raise ValueError("File must have a filename")
        
        artifact_folder = self.storage.uploads_dir / str(artifact_id)
        artifact_folder.mkdir(parents=True, exist_ok=True)
        file_location = artifact_folder / file.filename
        
        with open(file_location, "wb+") as buffer:
            buffer.write(file.file.read())
        
        return f"{artifact_id}/{file.filename}"
    
    def _delete_file(self, storage_path: str) -> None:
        """
        Delete file from physical storage.
        
        Args:
            storage_path: Path to the file in storage
        """
        file_path = self.storage.uploads_dir / storage_path
        if file_path.exists():
            file_path.unlink()
            
            # Remove parent directory if empty
            parent = file_path.parent
            if parent.exists() and not list(parent.iterdir()):
                parent.rmdir()
    
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
    return ArtifactManager(db)


__all__ = ["ArtifactManager", "get_artifact_manager"]
