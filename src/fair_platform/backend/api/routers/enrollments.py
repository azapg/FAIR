from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from fair_platform.backend.data.models.enrollment import Enrollment
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.user import User
from fair_platform.backend.api.schema.enrollment import (
    EnrollmentCreate,
    EnrollmentBulkCreate,
    EnrollmentRead,
    EnrollmentJoin,
)
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.core.security.permissions import (
    has_capability,
    has_capability_or_owner,
)

router = APIRouter()


@router.post("/", response_model=EnrollmentRead, status_code=status.HTTP_201_CREATED)
def create_enrollment(
    payload: EnrollmentCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """Enroll a user in a course. Only the course instructor or admin can enroll users."""
    course = db.get(Course, payload.course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    # Only admin or the course instructor can enroll students
    if not has_capability_or_owner(current_user, "manage_enrollments_any", course.instructor_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can enroll students",
        )

    # Verify the user to be enrolled exists
    student = db.get(User, payload.user_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check for duplicate enrollment
    existing = (
        db.query(Enrollment)
        .filter(
            Enrollment.user_id == payload.user_id,
            Enrollment.course_id == payload.course_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student is already enrolled in this course",
        )

    enrollment = Enrollment(
        id=uuid4(),
        user_id=payload.user_id,
        course_id=payload.course_id,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    return EnrollmentRead(
        id=enrollment.id,
        user_id=enrollment.user_id,
        course_id=enrollment.course_id,
        enrolled_at=enrollment.enrolled_at,
        user_name=student.name,
        course_name=course.name,
    )


@router.post("/bulk", response_model=list[EnrollmentRead], status_code=status.HTTP_201_CREATED)
def bulk_create_enrollments(
    payload: EnrollmentBulkCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """Bulk enroll multiple users in a course. Only the course instructor or admin can enroll users."""
    course = db.get(Course, payload.course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    if not has_capability_or_owner(current_user, "manage_enrollments_any", course.instructor_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can enroll students",
        )

    results = []
    for user_id in payload.user_ids:
        student = db.get(User, user_id)
        if not student:
            continue  # Skip non-existent users in bulk

        existing = (
            db.query(Enrollment)
            .filter(
                Enrollment.user_id == user_id,
                Enrollment.course_id == payload.course_id,
            )
            .first()
        )
        if existing:
            continue  # Skip already enrolled

        enrollment = Enrollment(
            id=uuid4(),
            user_id=user_id,
            course_id=payload.course_id,
        )
        db.add(enrollment)
        db.flush()
        results.append(EnrollmentRead(
            id=enrollment.id,
            user_id=enrollment.user_id,
            course_id=enrollment.course_id,
            enrolled_at=enrollment.enrolled_at,
            user_name=student.name,
            course_name=course.name,
        ))

    db.commit()
    return results


@router.post("/join", response_model=EnrollmentRead, status_code=status.HTTP_201_CREATED)
def join_course_by_code(
    payload: EnrollmentJoin,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """Allow a student to self-enroll using a class code."""
    if not has_capability(current_user, "join_course"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to join courses with a code",
        )

    course = (
        db.query(Course)
        .filter(Course.enrollment_code == payload.code)
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid enrollment code",
        )

    if not course.is_enrollment_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-enrollment is disabled for this course",
        )

    existing = (
        db.query(Enrollment)
        .filter(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id == course.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student is already enrolled in this course",
        )

    enrollment = Enrollment(
        id=uuid4(),
        user_id=current_user.id,
        course_id=course.id,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    return EnrollmentRead(
        id=enrollment.id,
        user_id=enrollment.user_id,
        course_id=enrollment.course_id,
        enrolled_at=enrollment.enrolled_at,
        user_name=current_user.name,
        course_name=course.name,
    )


@router.get("/", response_model=list[EnrollmentRead])
def list_enrollments(
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
    course_id: UUID | None = Query(None, description="Filter by course ID"),
    user_id: UUID | None = Query(None, description="Filter by user ID"),
):
    """List enrollments. Students can only see their own enrollments."""
    query = db.query(Enrollment)

    if has_capability(current_user, "update_any_course"):
        pass
    elif has_capability(current_user, "create_course"):
        query = query.join(Course).filter(
            or_(
                Enrollment.user_id == current_user.id,
                Course.instructor_id == current_user.id,
            )
        )
    else:
        # Students can only see their own enrollments
        query = query.filter(Enrollment.user_id == current_user.id)

    if course_id is not None:
        query = query.filter(Enrollment.course_id == course_id)
    if user_id is not None:
        query = query.filter(Enrollment.user_id == user_id)

    enrollments = query.all()
    results = []
    for e in enrollments:
        user = db.get(User, e.user_id)
        course = db.get(Course, e.course_id)
        results.append(EnrollmentRead(
            id=e.id,
            user_id=e.user_id,
            course_id=e.course_id,
            enrolled_at=e.enrolled_at,
            user_name=user.name if user else None,
            course_name=course.name if course else None,
        ))
    return results


@router.delete("/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_enrollment(
    enrollment_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """Remove an enrollment. Only the course instructor or admin can remove enrollments."""
    enrollment = db.get(Enrollment, enrollment_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found"
        )

    course = db.get(Course, enrollment.course_id)
    if not has_capability_or_owner(
        current_user, "manage_enrollments_any", course.instructor_id if course else None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can remove enrollments",
        )

    db.delete(enrollment)
    db.commit()
    return None


__all__ = ["router"]
