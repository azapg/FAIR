from uuid import UUID, uuid4
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload, selectinload

from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.api.schema.course import (
    CourseCreate,
    CourseRead,
    CourseUpdate,
    CourseDetailRead,
)
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.api.routers.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
def create_course(
    course: CourseCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    instructor = db.get(User, course.instructor_id)
    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Instructor not found"
        )

    if instructor.role == UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students cannot create courses",
        )

    if current_user.role != UserRole.admin and current_user.id != course.instructor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create a course for this instructor",
        )

    db_course = Course(
        id=uuid4(),
        name=course.name,
        description=course.description,
        instructor_id=course.instructor_id,
    )
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return {
        "id": db_course.id,
        "name": db_course.name,
        "description": db_course.description,
        "instructor_id": db_course.instructor_id,
        "instructor_name": instructor.name,
        "assignments_count": 0,
    }


@router.get("/", response_model=list[CourseRead])
def list_courses(
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
    instructor_id: Optional[UUID] = None,
):
    if current_user.role == UserRole.admin:
        query = db.query(Course).options(
            joinedload(Course.instructor),
            selectinload(Course.assignments),
        )

        if instructor_id is not None:
            query = query.filter(Course.instructor_id == instructor_id)
        courses = query.all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "instructor_id": c.instructor_id,
                "instructor_name": c.instructor.name if c.instructor else "",
                "assignments_count": len(c.assignments or []),
            }
            for c in courses
        ]

    # TODO: Students see nothing for now. Add enrollment table
    if current_user.role == UserRole.student:
        return []

    courses = (
        db.query(Course)
        .options(joinedload(Course.instructor), selectinload(Course.assignments))
        # Instructors (non-admin, non-student) see only their own courses.
        # maybe in the future we should just send all courses a user is enrolled or is instructing,
        # without caring about the role.
        .filter(Course.instructor_id == current_user.id)
        .all()
    )
    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "instructor_id": c.instructor_id,
            "instructor_name": c.instructor.name
            if c.instructor
            else "Unknown Instructor",
            "assignments_count": len(c.assignments or []),
        }
        for c in courses
    ]


@router.get("/{course_id}", response_model=Union[CourseRead, CourseDetailRead])
def get_course(
    course_id: UUID,
    detailed: bool = False,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    # TODO: Students cannot access individual course details for now because there's no enrollment table
    if current_user.role == UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students are not authorized to view course details",
        )

    course = (
        db.query(Course)
        .options(
            joinedload(Course.instructor),
            selectinload(Course.assignments),
            selectinload(Course.workflows),
        )
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    # Authorization: admin or the course instructor
    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can view this course",
        )

    if detailed:
        return {
            "id": course.id,
            "name": course.name,
            "description": course.description,
            "instructor": course.instructor,
            "assignments": course.assignments or [],
            "workflows": course.workflows or [],
        }

    return {
        "id": course.id,
        "name": course.name,
        "description": course.description,
        "instructor_id": course.instructor_id,
        "instructor_name": course.instructor.name if course.instructor else "",
        "assignments_count": len(course.assignments or []),
    }


@router.put("/{course_id}", response_model=CourseRead)
def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    course = (
        db.query(Course)
        .options(joinedload(Course.instructor), selectinload(Course.assignments))
        .filter(Course.id == course_id)
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can update this course",
        )

    if payload.instructor_id is not None:
        instructor = db.get(User, payload.instructor_id)
        if not instructor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Instructor not found"
            )

        if instructor.role == UserRole.student:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students cannot be assigned as instructors",
            )

        course.instructor_id = payload.instructor_id
        course.instructor = instructor

    if payload.name is not None:
        course.name = payload.name
    if payload.description is not None:
        course.description = payload.description

    db.add(course)
    db.commit()
    db.refresh(course)
    return {
        "id": course.id,
        "name": course.name,
        "description": course.description,
        "instructor_id": course.instructor_id,
        "instructor_name": course.instructor.name if course.instructor else "",
        "assignments_count": len(course.assignments or []),
    }


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can delete this course",
        )

    db.delete(course)
    db.commit()
    return None


__all__ = ["router"]
