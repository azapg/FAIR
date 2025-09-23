from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.workflow import Workflow
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.api.schema.workflow import WorkflowCreate, WorkflowRead, WorkflowUpdate
from fair_platform.backend.api.routers.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
def create_workflow(
        payload: WorkflowCreate,
        db: Session = Depends(session_dependency),
        current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.admin and current_user.role != UserRole.professor:
        raise HTTPException(status_code=403, detail="Not authorized to create workflows")

    course = db.get(Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found")

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the course instructor or admin can create workflows")

    wf = Workflow(
        id=uuid4(),
        course_id=payload.course_id,
        name=payload.name,
        description=payload.description,
        created_by=current_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf


@router.get("/", response_model=List[WorkflowRead])
def list_workflows(course_id: UUID | None = None, db: Session = Depends(session_dependency),
                   current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.admin or current_user.role != UserRole.professor:
        raise HTTPException(status_code=403, detail="Not authorized to list workflows")

    if course_id:
        course = db.get(Course, course_id)
        if not course:
            raise HTTPException(status_code=400, detail="Course not found")
        if current_user.role == UserRole.professor and course.instructor_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to list workflows for this course")

    q = db.query(Workflow)
    if course_id:
        q = q.filter(Workflow.course_id == course_id)
    return q.all()


@router.get("/{workflow_id}", response_model=WorkflowRead)
def get_workflow(workflow_id: UUID, db: Session = Depends(session_dependency), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.admin and current_user.role != UserRole.professor:
        raise HTTPException(status_code=403, detail="Not authorized to get workflow")

    # TODO: we should also check if the professor is the instructor of the course related to this workflow
    wf = db.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return wf


@router.put("/{workflow_id}", response_model=WorkflowRead)
def update_workflow(
        workflow_id: UUID,
        payload: WorkflowUpdate,
        db: Session = Depends(session_dependency),
        current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.admin and current_user.role != UserRole.professor:
        raise HTTPException(status_code=403, detail="Not authorized to update workflow")

    wf = db.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    course = db.get(Course, wf.course_id)
    if not course:
        raise HTTPException(status_code=400, detail="Cannot find course for this workflow. Data integrity issue?")

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the course instructor or admin can update this workflow")

    if payload.name is not None:
        wf.name = payload.name
    if payload.description is not None:
        wf.description = payload.description

    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(workflow_id: UUID, db: Session = Depends(session_dependency),
                    current_user: User = Depends(get_current_user)):
    wf = db.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    course = db.get(Course, wf.course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found")

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only the course instructor or admin can delete this workflow")

    db.delete(wf)
    db.commit()
    return None


__all__ = ["router"]
