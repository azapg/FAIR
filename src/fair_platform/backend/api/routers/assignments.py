from uuid import UUID, uuid4
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime
import json

from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.assignment import (
    Assignment,
)
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.artifact import ArtifactStatus, AccessLevel
from fair_platform.backend.api.schema.assignment import (
    AssignmentRead,
    AssignmentUpdate,
)
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.services.artifact_manager import get_artifact_manager

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
    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
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

    if current_user.role == UserRole.admin:
        return query.all()
    else:
        # TODO: Check enrollment once implemented
        return query.join(Course).filter(Course.instructor_id == current_user.id).all()

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

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can view this assignment",
        )

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

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
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

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can delete this assignment",
        )

    db.delete(assignment)
    db.commit()
    return None


__all__ = ["router"]
