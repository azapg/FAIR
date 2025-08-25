from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from data.models.course import Course
from data.models.user import User, UserRole
from api.schema.course import CourseCreate, CourseRead, CourseUpdate
from data.database import session_dependency
from api.routers.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
def create_course(
    course: CourseCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    instructor = db.get(User, course.instructor_id)
    if not instructor:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Instructor not found")

    if instructor.role == UserRole.student:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students cannot create courses")

    if current_user.role != UserRole.admin and current_user.id != course.instructor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create a course for this instructor")

    db_course = Course(
        id=uuid4(),
        name=course.name,
        description=course.description,
        instructor_id=course.instructor_id
    )
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course


@router.get("/", response_model=list[CourseRead])
def list_courses(db: Session = Depends(session_dependency)):
    return db.query(Course).all()


@router.get("/{course_id}", response_model=CourseRead)
def get_course(course_id: UUID, db: Session = Depends(session_dependency)):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course

@router.put("/{course_id}", response_model=CourseRead)
def update_course(
    course_id: UUID,
    payload: CourseUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")


    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the course instructor or admin can update this course")

    if payload.instructor_id is not None:
        instructor = db.get(User, payload.instructor_id)
        if not instructor:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Instructor not found")

        if instructor.role == UserRole.student:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students cannot be assigned as instructors")

        course.instructor_id = payload.instructor_id

    if payload.name is not None:
        course.name = payload.name
    if payload.description is not None:
        course.description = payload.description

    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: UUID, db: Session = Depends(session_dependency), current_user: User = Depends(get_current_user)):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the course instructor or admin can delete this course")

    db.delete(course)
    db.commit()
    return None


__all__ = ["router"]
