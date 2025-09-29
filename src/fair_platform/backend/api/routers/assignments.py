from uuid import UUID, uuid4
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.assignment import (
    Assignment,
    assignment_artifacts,
)
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.artifact import Artifact
from fair_platform.backend.api.schema.assignment import (
    AssignmentCreate,
    AssignmentRead,
    AssignmentUpdate,
)
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models.user import User, UserRole

router = APIRouter()


@router.post("/", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: AssignmentCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    course = db.get(Course, payload.course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found"
        )
    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can create assignments",
        )

    assignment = Assignment(
        id=uuid4(),
        course_id=payload.course_id,
        title=payload.title,
        description=payload.description,
        deadline=payload.deadline,
        max_grade=payload.max_grade,
    )
    db.add(assignment)
    db.commit()

    # link artifacts if provided
    if payload.artifacts:
        for artifact_id in payload.artifacts:
            if not db.get(Artifact, artifact_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Artifact {artifact_id} not found",
                )
            db.execute(
                assignment_artifacts.insert().values(
                    id=uuid4(),
                    assignment_id=assignment.id,
                    artifact_id=artifact_id,
                )
            )
        db.commit()

    db.refresh(assignment)
    return assignment


@router.get("/", response_model=List[AssignmentRead])
def list_assignments(
    db: Session = Depends(session_dependency),
    course_id: UUID = Query(None, description="Filter assignments by course ID"),
):
    query = db.query(Assignment)
    if course_id is not None:
        if not db.get(Course, course_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
            )
        query = query.filter(Assignment.course_id == course_id)
    return query.all()


@router.get("/{assignment_id}", response_model=AssignmentRead)
def get_assignment(assignment_id: UUID, db: Session = Depends(session_dependency)):
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
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

    # Replace artifact links if provided... maybe not the best idea though
    if payload.artifacts is not None:
        db.execute(
            delete(assignment_artifacts).where(
                lambda: assignment_artifacts.c.assignment_id == assignment.id
            )
        )
        db.commit()
        for artifact_id in payload.artifacts:
            if not db.get(Artifact, artifact_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Artifact {artifact_id} not found",
                )
            db.execute(
                assignment_artifacts.insert().values(
                    id=uuid4(),
                    assignment_id=assignment.id,
                    artifact_id=artifact_id,
                )
            )
        db.commit()

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
