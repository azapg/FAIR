from uuid import UUID, uuid4
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json

from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.assignment import (
    Assignment,
    AssignmentStatus,
)
from fair_platform.backend.data.models.submission import Submission
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.artifact import ArtifactStatus, AccessLevel
from fair_platform.backend.api.schema.assignment import (
    AssignmentRead,
    AssignmentUpdate,
    AssignmentStatusUpdate,
)
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.core.security.permissions import has_capability
from fair_platform.backend.data.models.user import User
from fair_platform.backend.data.models.enrollment import (
    CourseMembershipRole,
    Enrollment,
    EnrollmentStatus,
)
from fair_platform.backend.services.artifact_manager import get_artifact_manager
from fair_platform.backend.services.course_access import can_manage_course
from fair_platform.backend.services.notifications import notify_course_members

router = APIRouter()

@router.post("/", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    course_id: UUID = Form(...),
    title: str = Form(...),
    description: str = Form(None),
    deadline: str = Form(None),
    max_grade: str = Form(None),
    artifact_ids: str = Form(None),
    files: List[UploadFile] = File(None),
    allow_resubmissions: bool = Form(True),
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """
    Create an assignment with optional file uploads and/or existing artifact references.

    This endpoint supports both multipart/form-data (for file uploads) and can reference
    existing artifacts by ID. All operations are atomic - if any step fails, everything
    is rolled back.

    Form fields:
    - course_id: UUID of the course (required)
    - title: Assignment title (required)
    - description: Optional description text
    - deadline: Optional deadline in ISO format (YYYY-MM-DDTHH:MM:SS)
    - max_grade: Optional JSON object with grade structure: {"type": "points", "value": 100}
    - artifact_ids: Optional JSON array of existing artifact UUIDs: ["uuid1", "uuid2"]
    - files: Optional list of files to upload as new artifacts
    """
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found"
        )
    if not can_manage_course(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can create assignments",
        )

    try:
        max_grade_dict = None
        if max_grade:
            try:
                max_grade_dict = json.loads(max_grade)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid max_grade JSON. Expected format: {\"type\": \"points\", \"value\": 100}"
                )

        existing_artifact_ids = []
        if artifact_ids:
            try:
                existing_artifact_ids = json.loads(artifact_ids)
                if not isinstance(existing_artifact_ids, list):
                    raise ValueError("artifact_ids must be an array")
            except (json.JSONDecodeError, ValueError) as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid artifact_ids JSON. Expected array of UUIDs: {str(e)}"
                )

        deadline_dt = None
        if deadline:
            try:
                deadline_dt = datetime.fromisoformat(deadline)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid deadline format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
                )

        assignment = Assignment(
            id=uuid4(),
            course_id=course_id,
            title=title,
            description=description,
            deadline=deadline_dt,
            max_grade=max_grade_dict,
            status=AssignmentStatus.draft,
            allow_resubmissions=allow_resubmissions,
        )
        db.add(assignment)
        db.flush()

        manager = get_artifact_manager(db)

        if existing_artifact_ids:
            for artifact_id in existing_artifact_ids:
                try:
                    manager.attach_to_assignment(UUID(artifact_id), assignment.id, current_user)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid artifact ID format: {artifact_id}"
                    )

        if files:
            for file in files:
                artifact = manager.create_artifact(
                    file=file,
                    creator=current_user,
                    status=ArtifactStatus.attached,
                    access_level=AccessLevel.assignment,
                    course_id=course_id,
                    assignment_id=assignment.id,
                )
                assignment.artifacts.append(artifact)

        db.commit()
        db.refresh(assignment)
        return assignment

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create assignment: {str(e)}"
        )


@router.get("/", response_model=List[AssignmentRead])
def list_assignments(
    db: Session = Depends(session_dependency),
    course_id: UUID | None = Query(None, description="Filter assignments by course ID"),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Assignment)

    if course_id is not None:
        if not db.get(Course, course_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
            )

        query = query.filter(Assignment.course_id == course_id)

    if has_capability(current_user, "view_all_assignments"):
        return query.all()
    assignments = (
        query.join(Course)
        .outerjoin(
            Enrollment,
            and_(
                Enrollment.course_id == Course.id,
                Enrollment.user_id == current_user.id,
                Enrollment.status == EnrollmentStatus.active,
            ),
        )
        .filter(
            or_(
                Course.instructor_id == current_user.id,
                and_(
                    Enrollment.role == CourseMembershipRole.assistant,
                    Enrollment.user_id == current_user.id,
                ),
                and_(
                    Enrollment.user_id == current_user.id,
                    Assignment.status == AssignmentStatus.published,
                ),
            )
        )
        .distinct()
        .all()
    )
    return assignments

@router.get("/{assignment_id}", response_model=AssignmentRead)
def get_assignment(assignment_id: UUID, db: Session = Depends(session_dependency), current_user: User = Depends(get_current_user)):
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
        )

    course = db.get(Course, assignment.course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    if not can_manage_course(db, course, current_user):
        enrollment = (
            db.query(Enrollment)
            .filter(
                Enrollment.user_id == current_user.id,
                Enrollment.course_id == course.id,
                Enrollment.status == EnrollmentStatus.active,
            )
            .first()
        )
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the course instructor, admin, or enrolled users can view this assignment",
            )
        if assignment.status != AssignmentStatus.published:
            raise HTTPException(status_code=404, detail="Assignment not found")

    return assignment


@router.put("/{assignment_id}", response_model=AssignmentRead)
def update_assignment(
    assignment_id: UUID,
    payload: AssignmentUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
        )

    course = db.get(Course, assignment.course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found"
        )

    if not can_manage_course(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can update this assignment",
        )

    if payload.title is not None:
        assignment.title = payload.title
    if payload.description is not None:
        assignment.description = payload.description
    if payload.deadline is not None:
        assignment.deadline = payload.deadline
    if payload.max_grade is not None:
        assignment.max_grade = payload.max_grade
    if payload.allow_resubmissions is not None:
        assignment.allow_resubmissions = payload.allow_resubmissions

    db.add(assignment)
    db.commit()

    # TODO: Handle artifact updates if provided in payload

    db.refresh(assignment)
    return assignment


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
        )

    course = db.get(Course, assignment.course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found"
        )

    if not can_manage_course(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can delete this assignment",
        )

    submissions = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .all()
    )
    for submission in submissions:
        submission.artifacts.clear()
        submission.runs.clear()
        db.delete(submission)

    db.delete(assignment)
    db.commit()
    return None


@router.patch("/{assignment_id}/status", response_model=AssignmentRead)
def update_assignment_status(
    assignment_id: UUID,
    payload: AssignmentStatusUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    course = db.get(Course, assignment.course_id)
    if not course or not can_manage_course(db, course, current_user):
        raise HTTPException(status_code=403, detail="Only course staff can change publication status")
    if course.is_archived and payload.status == AssignmentStatus.published:
        raise HTTPException(status_code=400, detail="Assignments in archived courses cannot be published")
    assignment.status = payload.status
    if payload.status == AssignmentStatus.published and assignment.published_at is None:
        assignment.published_at = datetime.now(timezone.utc)
        notify_course_members(
            db,
            course_id=course.id,
            kind="assignment_published",
            title=f"New assignment: {assignment.title}",
            body=assignment.description,
            link=f"/courses/{course.id}/assignments/{assignment.id}",
            exclude_user_id=current_user.id,
        )
    db.commit()
    db.refresh(assignment)
    return assignment


__all__ = ["router"]
