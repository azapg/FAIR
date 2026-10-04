from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from fair_platform.backend.data.models.enrollment import Enrollment, EnrollmentStatus
from fair_platform.backend.data.models.lms_communication import Notification


def notify_course_members(
    db: Session,
    *,
    course_id: UUID,
    kind: str,
    title: str,
    body: str | None,
    link: str | None,
    exclude_user_id: UUID | None = None,
) -> None:
    user_ids = (
        db.query(Enrollment.user_id)
        .filter(
            Enrollment.course_id == course_id,
            Enrollment.status == EnrollmentStatus.active,
        )
        .distinct()
        .all()
    )
    for (user_id,) in user_ids:
        if user_id == exclude_user_id:
            continue
        db.add(
            Notification(
                id=uuid4(),
                user_id=user_id,
                kind=kind,
                title=title,
                body=body,
                link=link,
            )
        )


__all__ = ["notify_course_members"]
