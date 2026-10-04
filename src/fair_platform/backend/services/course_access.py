from uuid import UUID

from sqlalchemy.orm import Session

from fair_platform.backend.core.security.permissions import has_capability
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.enrollment import (
    CourseMembershipRole,
    Enrollment,
    EnrollmentStatus,
)
from fair_platform.backend.data.models.user import User


def active_membership(db: Session, course_id: UUID, user_id: UUID) -> Enrollment | None:
    return (
        db.query(Enrollment)
        .filter(
            Enrollment.course_id == course_id,
            Enrollment.user_id == user_id,
            Enrollment.status == EnrollmentStatus.active,
        )
        .first()
    )


def course_role(db: Session, course: Course, user: User) -> CourseMembershipRole | None:
    if course.instructor_id == user.id:
        return CourseMembershipRole.owner
    membership = active_membership(db, course.id, user.id)
    return membership.role if membership else None


def can_view_course(db: Session, course: Course, user: User) -> bool:
    return has_capability(user, "update_any_course") or course_role(db, course, user) is not None


def can_manage_course(db: Session, course: Course, user: User) -> bool:
    if has_capability(user, "update_any_course"):
        return True
    return course_role(db, course, user) in {
        CourseMembershipRole.owner,
        CourseMembershipRole.assistant,
    }


def can_own_course(db: Session, course: Course, user: User) -> bool:
    return has_capability(user, "update_any_course") or course_role(db, course, user) == CourseMembershipRole.owner
