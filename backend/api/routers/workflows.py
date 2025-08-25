from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from data.database import session_dependency
from data.models.workflow import Workflow
from data.models.course import Course
from data.models.user import User, UserRole
from api.schema.workflow import WorkflowCreate, WorkflowRead, WorkflowUpdate
from api.routers.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    course = db.get(Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found")

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the course instructor or admin can create workflows")

    if not db.get(User, payload.created_by):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Creator not found")

    if current_user.role != UserRole.admin and payload.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create workflow on behalf of another user")

    wf = Workflow(
        id=uuid4(),
        course_id=payload.course_id,
        name=payload.name,
        description=payload.description,
        created_by=payload.created_by,
        created_at=datetime.now(timezone.utc),
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf


@router.get("/", response_model=List[WorkflowRead])
def list_workflows(course_id: UUID | None = None, db: Session = Depends(session_dependency)):
    q = db.query(Workflow)
    if course_id:
        q = q.filter(Workflow.course_id == course_id)
    return q.all()


@router.get("/{workflow_id}", response_model=WorkflowRead)
def get_workflow(workflow_id: UUID, db: Session = Depends(session_dependency)):
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
    wf = db.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    course = db.get(Course, wf.course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found")

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the course instructor or admin can update this workflow")

    if payload.course_id is not None:
        if not db.get(Course, payload.course_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found")
        wf.course_id = payload.course_id
    if payload.name is not None:
        wf.name = payload.name
    if payload.description is not None:
        wf.description = payload.description
    if payload.created_by is not None:
        if not db.get(User, payload.created_by):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Creator not found")
        if current_user.role != UserRole.admin and payload.created_by != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to change creator")
        wf.created_by = payload.created_by

    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(workflow_id: UUID, db: Session = Depends(session_dependency), current_user: User = Depends(get_current_user)):
    wf = db.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    course = db.get(Course, wf.course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found")

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the course instructor or admin can delete this workflow")

    db.delete(wf)
    db.commit()
    return None


__all__ = ["router"]

