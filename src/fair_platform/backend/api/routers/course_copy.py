from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.course_copy import (
    CourseCopyPreview,
    CourseCopyRequest,
    CourseCopyResult,
    CourseTemplateCreate,
    CourseTemplateRead,
)
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.lms_course_copy import (
    CourseCopyJob,
    CourseTemplate,
)
from fair_platform.backend.data.models.user import User
from fair_platform.backend.services.course_access import can_manage_course
from fair_platform.backend.services.course_copy import (
    CourseCopyConflict,
    execute,
    preview,
)

router = APIRouter()


def _source(db: Session, course_id: UUID, user: User) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    if not can_manage_course(db, course, user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only course staff can copy a course"
        )
    return course


def _result(job: CourseCopyJob) -> CourseCopyResult:
    return CourseCopyResult(
        job_id=job.id,
        destination_course_id=job.destination_course_id,
        status=job.status,
        mapping=job.mapping,
        error_message=job.error,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


def _template(template: CourseTemplate) -> CourseTemplateRead:
    return CourseTemplateRead(
        id=template.id,
        name=template.name,
        source_course_id=template.source_course_id,
        selection=template.selection,
        date_policy=template.date_policy,
        date_shift_days=template.date_shift_days,
        created_at=template.created_at,
    )


@router.post("/courses/{course_id}/copy-preview", response_model=CourseCopyPreview)
def course_copy_preview(
    course_id: UUID,
    payload: CourseCopyRequest,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    return preview(db, _source(db, course_id, current_user), payload)


@router.post("/courses/{course_id}/copy", response_model=CourseCopyResult)
def copy_course(
    course_id: UUID,
    payload: CourseCopyRequest,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    try:
        return _result(
            execute(db, _source(db, course_id, current_user), current_user.id, payload)
        )
    except CourseCopyConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.get("/course-copy-jobs/{job_id}", response_model=CourseCopyResult)
def get_copy_job(
    job_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    job = db.get(CourseCopyJob, job_id)
    if job is None or job.requested_by_user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Copy job not found")
    return _result(job)


@router.post(
    "/courses/{course_id}/templates",
    response_model=CourseTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def save_template(
    course_id: UUID,
    payload: CourseTemplateCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    source = _source(db, course_id, current_user)
    template = CourseTemplate(
        source_course_id=source.id,
        owner_user_id=current_user.id,
        name=payload.name,
        selection=payload.selection.model_dump(),
        date_policy=payload.date_policy,
        date_shift_days=payload.date_shift_days,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return _template(template)


@router.get("/course-templates", response_model=list[CourseTemplateRead])
def list_templates(
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    return [
        _template(item)
        for item in db.query(CourseTemplate)
        .filter_by(owner_user_id=current_user.id)
        .order_by(CourseTemplate.created_at.desc())
    ]


def _owned_template(db: Session, template_id: UUID, user: User) -> CourseTemplate:
    template = db.get(CourseTemplate, template_id)
    if template is None or template.owner_user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    return template


@router.post(
    "/course-templates/{template_id}/instantiate", response_model=CourseCopyResult
)
def instantiate_template(
    template_id: UUID,
    payload: CourseCopyRequest,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    template = _owned_template(db, template_id, current_user)
    payload.selection = payload.selection.model_validate(template.selection)
    payload.date_policy, payload.date_shift_days = (
        template.date_policy,
        template.date_shift_days,
    )
    return copy_course(template.source_course_id, payload, db, current_user)
