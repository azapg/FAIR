from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.student_dashboard import (
    StudentCourseGrades,
    StudentDashboard,
)
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.enrollment import (
    CourseMembershipRole,
    Enrollment,
    EnrollmentStatus,
)
from fair_platform.backend.data.models.user import User
from fair_platform.backend.core.security.permissions import coerce_user_role
from fair_platform.backend.data.models.user import UserRole
from fair_platform.backend.services.course_access import active_membership
from fair_platform.backend.services.student_dashboard import (
    resilient_student_dashboard,
    student_course_grades,
)


router = APIRouter()


def _require_learner_context(db: Session, user: User) -> None:
    active_staff_membership = (
        db.query(Enrollment.id)
        .filter(
            Enrollment.user_id == user.id,
            Enrollment.role.in_(
                [CourseMembershipRole.owner, CourseMembershipRole.assistant]
            ),
            Enrollment.status == EnrollmentStatus.active,
        )
        .first()
    )
    if coerce_user_role(user.role) != UserRole.user or active_staff_membership:
        raise HTTPException(
            status_code=403,
            detail="Learner views are unavailable while using a staff account",
        )


def _student_course(db: Session, course_id: UUID, user: User) -> Course:
    _require_learner_context(db, user)
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    membership = active_membership(db, course_id, user.id)
    if membership is None or membership.role != CourseMembershipRole.student:
        raise HTTPException(
            status_code=403,
            detail="Only an active student can view their course grades",
        )
    return course


@router.get("/student/dashboard", response_model=StudentDashboard)
def get_student_dashboard(
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> StudentDashboard:
    # Do not infer a private learner context for staff or administrators.
    _require_learner_context(db, current_user)
    has_student_membership = (
        db.query(Enrollment)
        .filter(
            Enrollment.user_id == current_user.id,
            Enrollment.role == CourseMembershipRole.student,
            Enrollment.status == EnrollmentStatus.active,
        )
        .first()
    )
    if has_student_membership is None:
        raise HTTPException(
            status_code=403,
            detail="A student enrollment is required for the learner dashboard",
        )
    return StudentDashboard.model_validate(
        resilient_student_dashboard(db, current_user.id)
    )


@router.get("/courses/{course_id}/grades", response_model=StudentCourseGrades)
def get_student_course_grades(
    course_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> StudentCourseGrades:
    course = _student_course(db, course_id, current_user)
    return StudentCourseGrades.model_validate(
        student_course_grades(db, course, current_user.id)
    )


__all__ = ["router"]
