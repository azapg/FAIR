from uuid import UUID, uuid4
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy import delete
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
    AssignmentCreate,
    AssignmentRead,
    AssignmentUpdate,
)
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.services.artifact_manager import get_artifact_manager

router = APIRouter()


@router.post("/", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: AssignmentCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """Create assignment and optionally attach existing artifacts."""
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

    try:
        assignment = Assignment(
            id=uuid4(),
            course_id=payload.course_id,
            title=payload.title,
            description=payload.description,
            deadline=payload.deadline,
            max_grade=payload.max_grade,
        )
        db.add(assignment)
        db.flush()

        if payload.artifacts:
            manager = get_artifact_manager(db)
            
            for artifact_id in payload.artifacts:
                manager.attach_to_assignment(artifact_id, assignment.id, current_user)
        
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
    course_id: UUID = Query(None, description="Filter assignments by course ID"),
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
def get_assignment(assignment_id: UUID, db: Session = Depends(session_dependency)):
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
        )
    # TODO: Permission checks
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


@router.post("/create-with-files", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
async def create_assignment_with_files(
    course_id: UUID = Form(...),
    title: str = Form(...),
    description: str = Form(None),
    deadline: str = Form(None),
    max_grade: str = Form(...),
    files: List[UploadFile] = File(None),
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """
    Create an assignment with file uploads atomically.
    
    This endpoint creates the assignment and uploads artifacts in a single
    transaction. If any step fails, everything is rolled back, preventing
    orphaned artifacts.
    
    Form fields:
    - course_id: UUID of the course
    - title: Assignment title
    - description: Optional description
    - deadline: Optional deadline (ISO format string)
    - max_grade: JSON object with max grade structure
    - files: Optional list of files to upload
    """
    try:
        course = db.get(Course, course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course not found"
            )
        
        if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the course instructor or admin can create assignments",
            )
        
        # TODO: I have to standarize the Grade schema
        try:
            max_grade_dict = json.loads(max_grade)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid max_grade JSON"
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
        
        if files:
            manager = get_artifact_manager(db)
            
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
            detail=f"Failed to create assignment with files: {str(e)}"
        )


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
