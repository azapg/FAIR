"""Explicit, allowlist-only LMS course copying.

Only authoring records named in this module are copied. Learner and operational
graphs are measured for the preview, but are never traversed during execution.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from threading import Lock, RLock
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.enrollment import (
    CourseMembershipRole,
    Enrollment,
    EnrollmentStatus,
)
from fair_platform.backend.data.models.execution import Execution
from fair_platform.backend.data.models.flow import Flow, FlowVersion
from fair_platform.backend.data.models.lms_communication import (
    CourseComment,
    CoursePost,
    SubmissionComment,
)
from fair_platform.backend.data.models.lms_content import (
    CourseContentVisibility,
    CourseItem,
    CourseSection,
)
from fair_platform.backend.data.models.lms_course_copy import CourseCopyJob
from fair_platform.backend.data.models.lms_events import ActivityEvent
from fair_platform.backend.data.models.lms_gradebook import (
    GradeCategory,
    GradeEntry,
    GradeItem,
)
from fair_platform.backend.data.models.lms_quiz import (
    Question,
    QuestionBank,
    QuestionVersion,
    Quiz,
    QuizAttempt,
    QuizQuestion,
)
from fair_platform.backend.data.models.rubric import Rubric
from fair_platform.backend.data.models.submission import Submission
from fair_platform.backend.services.flow_service import flow_version_hash


COPY_KINDS = (
    "sections",
    "items",
    "artifacts",
    "assignments",
    "rubrics",
    "grade_categories",
    "grade_items",
    "question_banks",
    "questions",
    "question_versions",
    "quizzes",
    "flows",
    "flow_versions",
)
SELECTION_FOR_KIND = {
    "sections": "content",
    "items": "content",
    "artifacts": "content",
    "assignments": "assignments",
    "rubrics": "rubrics",
    "grade_categories": "gradebook",
    "grade_items": "gradebook",
    "question_banks": "quizzes",
    "questions": "quizzes",
    "question_versions": "quizzes",
    "quizzes": "quizzes",
    "flows": "flows",
    "flow_versions": "flows",
}
SECRET_KEYS = {
    "accesskey",
    "accesskeyid",
    "apikey",
    "authorization",
    "clientsecret",
    "credential",
    "credentials",
    "password",
    "privatekey",
    "refreshtoken",
    "secret",
    "secretkey",
    "token",
}
_SQLITE_JOB_LOCKS: dict[UUID, RLock] = {}
_SQLITE_JOB_LOCKS_GUARD = Lock()


class CourseCopyConflict(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _snapshot(payload: Any) -> dict[str, Any]:
    return payload.model_dump(mode="json", exclude={"idempotency_key"})


def request_fingerprint(payload: Any) -> str:
    encoded = json.dumps(
        _snapshot(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _normalized_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _without_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_secrets(child)
            for key, child in value.items()
            if not _is_secret_key(str(key))
        }
    if isinstance(value, list):
        return [_without_secrets(child) for child in value]
    return deepcopy(value)


def _is_secret_key(key: str) -> bool:
    normalized = _normalized_key(key)
    return normalized in SECRET_KEYS or any(
        token in normalized
        for token in ("secret", "password", "token", "credential", "privatekey")
    )


def _count(db: Session, model: type, **filters: Any) -> int:
    return db.query(model).filter_by(**filters).count()


def _source_assignment_ids(db: Session, course_id: UUID) -> list[UUID]:
    return list(
        db.scalars(select(Assignment.id).where(Assignment.course_id == course_id))
    )


def _excluded_counts(db: Session, source: Course) -> dict[str, int]:
    assignment_ids = _source_assignment_ids(db, source.id)
    submission_ids = (
        list(
            db.scalars(
                select(Submission.id).where(
                    Submission.assignment_id.in_(assignment_ids)
                )
            )
        )
        if assignment_ids
        else []
    )
    return {
        "enrollments": max(_count(db, Enrollment, course_id=source.id), 0),
        "submissions": (
            db.query(Submission)
            .filter(Submission.assignment_id.in_(assignment_ids))
            .count()
            if assignment_ids
            else 0
        ),
        "submission_comments": (
            db.query(SubmissionComment)
            .filter(SubmissionComment.submission_id.in_(submission_ids))
            .count()
            if submission_ids
            else 0
        ),
        "course_posts": _count(db, CoursePost, course_id=source.id),
        "course_comments": (
            db.query(CourseComment)
            .join(CoursePost, CoursePost.id == CourseComment.post_id)
            .filter(CoursePost.course_id == source.id)
            .count()
        ),
        "grade_entries": _count(db, GradeEntry, course_id=source.id),
        "quiz_attempts": _count(db, QuizAttempt, course_id=source.id),
        # The legacy notification table has no course/source scope, so it is
        # excluded by construction but cannot be attributed to this course.
        "notifications": 0,
        "activity_events": _count(db, ActivityEvent, course_id=source.id),
        "executions": _count(db, Execution, course_id=source.id),
        "invite_codes": 1 if source.enrollment_code else 0,
    }


def _supported_content_item(item: CourseItem, selection: Any) -> bool:
    if item.resource_type is None:
        return True
    if item.resource_type == "artifact":
        return False
    if item.resource_type == "assignment":
        return selection.assignments
    if item.resource_type == "quiz":
        return selection.quizzes
    return False


def preview(db: Session, source: Course, payload: Any) -> dict[str, Any]:
    selection = payload.selection
    copied = {kind: 0 for kind in COPY_KINDS}
    transformed = {
        "publishable_to_draft": 0,
        "dates_cleared": 0,
        "dates_shifted": 0,
        "flow_secrets_removed": 0,
    }
    unsupported: dict[str, int] = defaultdict(int)
    warnings = [
        "All learner and operational records are excluded.",
        "All copied publishable content becomes draft.",
    ]

    items: list[CourseItem] = []
    if selection.content:
        copied["sections"] = _count(db, CourseSection, course_id=source.id)
        items = db.query(CourseItem).filter_by(course_id=source.id).all()
        for item in items:
            if _supported_content_item(item, selection):
                copied["items"] += 1
            else:
                unsupported[f"{item.resource_type or 'unknown'}_items"] += 1

    if selection.assignments:
        copied["assignments"] = _count(db, Assignment, course_id=source.id)
    if selection.rubrics:
        copied["rubrics"] = (
            db.query(func.count(func.distinct(Assignment.rubric_id)))
            .filter(
                Assignment.course_id == source.id,
                Assignment.rubric_id.is_not(None),
            )
            .scalar()
            or 0
        )
    if selection.gradebook:
        copied["grade_categories"] = _count(db, GradeCategory, course_id=source.id)
        grade_items = db.query(GradeItem).filter_by(course_id=source.id).all()
        for item in grade_items:
            source_copied = (
                item.source_type is None
                or (item.source_type == "assignment" and selection.assignments)
                or (item.source_type == "quiz" and selection.quizzes)
            )
            if source_copied:
                copied["grade_items"] += 1
            else:
                unsupported[f"{item.source_type or 'unknown'}_grade_items"] += 1
    if selection.quizzes:
        copied["question_banks"] = _count(db, QuestionBank, course_id=source.id)
        copied["questions"] = _count(db, Question, course_id=source.id)
        copied["question_versions"] = _count(db, QuestionVersion, course_id=source.id)
        copied["quizzes"] = _count(db, Quiz, course_id=source.id)
    if selection.flows:
        flows = db.query(Flow).filter_by(course_id=source.id).all()
        copied["flows"] = len(flows)
        copied["flow_versions"] = sum(len(flow.versions) for flow in flows)
        transformed["flow_secrets_removed"] = sum(
            1
            for flow in flows
            for version in flow.versions
            if (
                _without_secrets(version.definition) != version.definition
                or _without_secrets(version.capability_pins) != version.capability_pins
                or _without_secrets(version.config_snapshot) != version.config_snapshot
            )
        )

    transformed["publishable_to_draft"] = sum(
        copied[kind]
        for kind in ("sections", "items", "assignments", "quizzes", "flow_versions")
    )
    dated = 0
    if selection.assignments:
        dated += (
            db.query(Assignment)
            .filter(Assignment.course_id == source.id, Assignment.deadline.is_not(None))
            .count()
        )
    if selection.quizzes:
        dated += (
            db.query(Quiz)
            .filter(
                Quiz.course_id == source.id,
                (Quiz.opens_at.is_not(None) | Quiz.closes_at.is_not(None)),
            )
            .count()
        )
    transformed[
        "dates_shifted" if payload.date_policy == "shift" else "dates_cleared"
    ] = dated

    skipped = _excluded_counts(db, source)
    for kind, selection_name in SELECTION_FOR_KIND.items():
        if not getattr(selection, selection_name):
            skipped[kind] = _count_for_kind(db, source.id, kind)
    if unsupported:
        warnings.append(
            "Unsupported or unselected resource-linked items are omitted and listed below."
        )
    return {
        "copied": copied,
        "transformed": transformed,
        "skipped": skipped,
        "unsupported": dict(unsupported),
        "date_policy": payload.date_policy,
        "date_shift_days": payload.date_shift_days,
        "warnings": warnings,
        "objects": _preview_objects(db, source.id, payload),
    }


def _preview_objects(
    db: Session, source_id: UUID, payload: Any
) -> list[dict[str, Any]]:
    selection = payload.selection
    result: list[dict[str, Any]] = []

    def add(
        source_id: UUID,
        object_type: str,
        title: str,
        action: str,
        reason: str,
    ) -> None:
        result.append(
            {
                "source_id": source_id,
                "object_type": object_type,
                "title": title,
                "action": action,
                "reason": reason,
            }
        )

    for section in db.query(CourseSection).filter_by(course_id=source_id).all():
        add(
            section.id,
            "section",
            section.title,
            "transform" if selection.content else "skip",
            "Copied as draft" if selection.content else "Content was not selected",
        )
    for item in db.query(CourseItem).filter_by(course_id=source_id).all():
        if not selection.content:
            action, reason = "skip", "Content was not selected"
        elif _supported_content_item(item, selection):
            action, reason = "transform", "Copied as draft with fresh references"
        else:
            action, reason = (
                "unsupported",
                f"{item.resource_type or 'Unknown'} resources cannot be copied safely",
            )
        add(item.id, "course_item", item.title, action, reason)

    assignments = db.query(Assignment).filter_by(course_id=source_id).all()
    for assignment in assignments:
        add(
            assignment.id,
            "assignment",
            assignment.title,
            "transform" if selection.assignments else "skip",
            (
                "Copied as draft with the selected date policy"
                if selection.assignments
                else "Assignments were not selected"
            ),
        )
    rubric_ids = {
        assignment.rubric_id for assignment in assignments if assignment.rubric_id
    }
    for rubric in (
        db.query(Rubric).filter(Rubric.id.in_(rubric_ids)).all() if rubric_ids else []
    ):
        add(
            rubric.id,
            "rubric",
            rubric.name,
            "copy" if selection.rubrics else "skip",
            "Copied for linked assignments"
            if selection.rubrics
            else "Rubrics were not selected",
        )

    for category in db.query(GradeCategory).filter_by(course_id=source_id).all():
        add(
            category.id,
            "grade_category",
            category.name,
            "copy" if selection.gradebook else "skip",
            "Gradebook structure selected"
            if selection.gradebook
            else "Gradebook was not selected",
        )
    for item in db.query(GradeItem).filter_by(course_id=source_id).all():
        compatible = (
            item.source_type is None
            or (item.source_type == "assignment" and selection.assignments)
            or (item.source_type == "quiz" and selection.quizzes)
        )
        if not selection.gradebook:
            action, reason = "skip", "Gradebook was not selected"
        elif compatible:
            action, reason = "copy", "Copied with a fresh internal source reference"
        else:
            action, reason = "unsupported", "Its source resource was not selected"
        add(item.id, "grade_item", item.title, action, reason)

    quiz_models: list[tuple[type, str, str]] = [
        (QuestionBank, "question_bank", "name"),
        (Question, "question", "title"),
        (Quiz, "quiz", "title"),
    ]
    for model, object_type, title_field in quiz_models:
        for value in db.query(model).filter_by(course_id=source_id).all():
            is_quiz = object_type == "quiz"
            add(
                value.id,
                object_type,
                str(getattr(value, title_field)),
                ("transform" if is_quiz else "copy") if selection.quizzes else "skip",
                (
                    "Copied as draft with the selected date policy"
                    if is_quiz and selection.quizzes
                    else "Quiz authoring graph selected"
                    if selection.quizzes
                    else "Quizzes were not selected"
                ),
            )
    for version in db.query(QuestionVersion).filter_by(course_id=source_id).all():
        add(
            version.id,
            "question_version",
            version.prompt[:120],
            "copy" if selection.quizzes else "skip",
            "Immutable question version selected"
            if selection.quizzes
            else "Quizzes were not selected",
        )

    for flow in db.query(Flow).filter_by(course_id=source_id).all():
        add(
            flow.id,
            "flow",
            flow.name,
            "copy" if selection.flows else "skip",
            "Flow definitions selected"
            if selection.flows
            else "Flows were not selected",
        )
        for version in flow.versions:
            add(
                version.id,
                "flow_version",
                f"{flow.name} version {version.ordinal}",
                "transform" if selection.flows else "skip",
                "Copied as draft with secrets removed"
                if selection.flows
                else "Flows were not selected",
            )
    return sorted(
        result,
        key=lambda item: (item["object_type"], item["title"], str(item["source_id"])),
    )


def _count_for_kind(db: Session, course_id: UUID, kind: str) -> int:
    model_by_kind = {
        "sections": CourseSection,
        "items": CourseItem,
        "assignments": Assignment,
        "grade_categories": GradeCategory,
        "grade_items": GradeItem,
        "question_banks": QuestionBank,
        "questions": Question,
        "question_versions": QuestionVersion,
        "quizzes": Quiz,
        "flows": Flow,
    }
    if kind == "artifacts":
        return 0
    if kind == "rubrics":
        return (
            db.query(func.count(func.distinct(Assignment.rubric_id)))
            .filter(
                Assignment.course_id == course_id,
                Assignment.rubric_id.is_not(None),
            )
            .scalar()
            or 0
        )
    if kind == "flow_versions":
        return (
            db.query(FlowVersion)
            .join(Flow, Flow.id == FlowVersion.flow_id)
            .filter(Flow.course_id == course_id)
            .count()
        )
    return _count(db, model_by_kind[kind], course_id=course_id)


def create_or_resume_job(
    db: Session, source: Course, actor_id: UUID, payload: Any
) -> CourseCopyJob:
    fingerprint = request_fingerprint(payload)
    job = (
        db.query(CourseCopyJob)
        .filter_by(
            requested_by_user_id=actor_id,
            idempotency_key=payload.idempotency_key,
        )
        .one_or_none()
    )
    if job is not None:
        if job.source_course_id != source.id or job.request_fingerprint != fingerprint:
            raise CourseCopyConflict(
                "Idempotency key was used with a different copy request"
            )
        return job

    job = CourseCopyJob(
        id=uuid4(),
        source_course_id=source.id,
        requested_by_user_id=actor_id,
        idempotency_key=payload.idempotency_key,
        request_fingerprint=fingerprint,
        request_snapshot=_snapshot(payload),
        status="pending",
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        job = (
            db.query(CourseCopyJob)
            .filter_by(
                requested_by_user_id=actor_id,
                idempotency_key=payload.idempotency_key,
            )
            .one()
        )
        if job.source_course_id != source.id or job.request_fingerprint != fingerprint:
            raise CourseCopyConflict(
                "Idempotency key was used with a different copy request"
            )
        return job
    db.refresh(job)
    return job


def _job_lock(job_id: UUID) -> RLock:
    with _SQLITE_JOB_LOCKS_GUARD:
        return _SQLITE_JOB_LOCKS.setdefault(job_id, RLock())


def _lock_job(db: Session, job_id: UUID) -> CourseCopyJob:
    return (
        db.query(CourseCopyJob)
        .filter(CourseCopyJob.id == job_id)
        .populate_existing()
        .with_for_update()
        .one()
    )


def execute(db: Session, source: Course, actor_id: UUID, payload: Any) -> CourseCopyJob:
    job = create_or_resume_job(db, source, actor_id, payload)
    sqlite_lock = _job_lock(job.id) if db.get_bind().dialect.name == "sqlite" else None
    if sqlite_lock is not None:
        sqlite_lock.acquire()
    try:
        job = _lock_job(db, job.id)
        if job.status in {"completed", "running"}:
            db.commit()
            return job
        job.status = "running"
        job.error = None
        job.started_at = _now()
        job.completed_at = None
        db.commit()

        try:
            with db.begin_nested():
                mapping = _copy_graph(db, source, actor_id, payload)
                job = db.get(CourseCopyJob, job.id)
                job.destination_course_id = UUID(mapping["courses"][str(source.id)])
                job.mapping = mapping
            job.status = "completed"
            job.completed_at = _now()
            db.commit()
            db.refresh(job)
            return job
        except Exception as exc:
            db.rollback()
            job = db.get(CourseCopyJob, job.id)
            job.status = "failed"
            job.error = str(exc)[:4000]
            job.destination_course_id = None
            job.mapping = {}
            job.completed_at = _now()
            db.commit()
            db.refresh(job)
            return job
    finally:
        if sqlite_lock is not None:
            sqlite_lock.release()


def _copy_graph(
    db: Session, source: Course, actor_id: UUID, payload: Any
) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {kind: {} for kind in (*COPY_KINDS, "courses")}
    destination = Course(
        id=uuid4(),
        name=payload.name,
        description=(
            payload.description
            if payload.description is not None
            else source.description
        ),
        instructor_id=actor_id,
        organization_id=source.organization_id,
        section=payload.section,
        term=payload.term,
        is_enrollment_enabled=False,
        enrollment_code=None,
        is_archived=False,
        copied_from_id=source.id,
    )
    db.add(destination)
    db.flush()
    mapping["courses"][str(source.id)] = str(destination.id)
    db.add(
        Enrollment(
            id=uuid4(),
            course_id=destination.id,
            user_id=actor_id,
            role=CourseMembershipRole.owner,
            status=EnrollmentStatus.active,
        )
    )

    shift = (
        timedelta(days=payload.date_shift_days)
        if payload.date_policy == "shift"
        else None
    )

    def copied_date(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value + shift if shift is not None else None

    if payload.selection.content:
        _copy_sections(db, source.id, destination.id, mapping)
    if payload.selection.rubrics:
        _copy_rubrics(db, source.id, actor_id, mapping)
    if payload.selection.assignments:
        _copy_assignments(
            db,
            source.id,
            destination.id,
            payload.selection.rubrics,
            copied_date,
            mapping,
        )
    if payload.selection.quizzes:
        _copy_quizzes(db, source.id, destination.id, actor_id, copied_date, mapping)
    if payload.selection.flows:
        _copy_flows(db, source.id, destination.id, actor_id, mapping)
    if payload.selection.gradebook:
        _copy_gradebook(db, source.id, destination.id, mapping)
    if payload.selection.content:
        _copy_course_items(db, source.id, destination.id, mapping, payload)
    return mapping


def _copy_sections(
    db: Session,
    source_id: UUID,
    destination_id: UUID,
    mapping: dict[str, dict[str, str]],
) -> None:
    sections = (
        db.query(CourseSection)
        .filter_by(course_id=source_id)
        .order_by(CourseSection.position, CourseSection.id)
        .all()
    )
    for old in sections:
        new = CourseSection(
            id=uuid4(),
            course_id=destination_id,
            title=old.title,
            summary=old.summary,
            position=old.position,
            visibility=CourseContentVisibility.draft,
            copied_from_id=old.id,
        )
        db.add(new)
        mapping["sections"][str(old.id)] = str(new.id)


def _copy_rubrics(
    db: Session,
    source_id: UUID,
    actor_id: UUID,
    mapping: dict[str, dict[str, str]],
) -> None:
    rubric_ids = list(
        db.scalars(
            select(Assignment.rubric_id)
            .where(
                Assignment.course_id == source_id,
                Assignment.rubric_id.is_not(None),
            )
            .distinct()
        )
    )
    for old in (
        db.query(Rubric).filter(Rubric.id.in_(rubric_ids)).all() if rubric_ids else []
    ):
        new = Rubric(
            id=uuid4(),
            name=old.name,
            created_by_id=actor_id,
            content=deepcopy(old.content),
        )
        db.add(new)
        mapping["rubrics"][str(old.id)] = str(new.id)


def _copy_assignments(
    db: Session,
    source_id: UUID,
    destination_id: UUID,
    copy_rubrics: bool,
    copied_date: Any,
    mapping: dict[str, dict[str, str]],
) -> None:
    for old in db.query(Assignment).filter_by(course_id=source_id).all():
        rubric_id = (
            mapping["rubrics"].get(str(old.rubric_id))
            if copy_rubrics and old.rubric_id
            else None
        )
        new = Assignment(
            id=uuid4(),
            course_id=destination_id,
            title=old.title,
            description=old.description,
            deadline=copied_date(old.deadline),
            max_grade=deepcopy(old.max_grade),
            status="draft",
            published_at=None,
            rubric_id=UUID(rubric_id) if rubric_id else None,
            allow_resubmissions=old.allow_resubmissions,
        )
        db.add(new)
        mapping["assignments"][str(old.id)] = str(new.id)


def _copy_quizzes(
    db: Session,
    source_id: UUID,
    destination_id: UUID,
    actor_id: UUID,
    copied_date: Any,
    mapping: dict[str, dict[str, str]],
) -> None:
    for old in db.query(QuestionBank).filter_by(course_id=source_id).all():
        new = QuestionBank(
            id=uuid4(),
            course_id=destination_id,
            name=old.name,
            description=old.description,
        )
        db.add(new)
        mapping["question_banks"][str(old.id)] = str(new.id)
    for old in db.query(Question).filter_by(course_id=source_id).all():
        bank_id = mapping["question_banks"].get(str(old.bank_id))
        if bank_id is None:
            continue
        new = Question(
            id=uuid4(),
            course_id=destination_id,
            bank_id=UUID(bank_id),
            title=old.title,
        )
        db.add(new)
        mapping["questions"][str(old.id)] = str(new.id)
    for old in db.query(QuestionVersion).filter_by(course_id=source_id).all():
        question_id = mapping["questions"].get(str(old.question_id))
        if question_id is None:
            continue
        new = QuestionVersion(
            id=uuid4(),
            course_id=destination_id,
            question_id=UUID(question_id),
            version_number=old.version_number,
            kind=old.kind,
            prompt=old.prompt,
            options=deepcopy(old.options),
            correct_option_id=old.correct_option_id,
            default_points=old.default_points,
            explanation=old.explanation,
            authored_by_user_id=actor_id,
        )
        db.add(new)
        mapping["question_versions"][str(old.id)] = str(new.id)
    for old in db.query(Quiz).filter_by(course_id=source_id).all():
        new = Quiz(
            id=uuid4(),
            course_id=destination_id,
            title=old.title,
            instructions=old.instructions,
            status="draft",
            release_policy=old.release_policy,
            attempt_limit=old.attempt_limit,
            opens_at=copied_date(old.opens_at),
            closes_at=copied_date(old.closes_at),
            created_by_user_id=actor_id,
            published_at=None,
            closed_at=None,
        )
        db.add(new)
        mapping["quizzes"][str(old.id)] = str(new.id)
    for old in db.query(QuizQuestion).filter_by(course_id=source_id).all():
        quiz_id = mapping["quizzes"].get(str(old.quiz_id))
        version_id = mapping["question_versions"].get(str(old.question_version_id))
        if quiz_id is None or version_id is None:
            continue
        db.add(
            QuizQuestion(
                id=uuid4(),
                course_id=destination_id,
                quiz_id=UUID(quiz_id),
                question_version_id=UUID(version_id),
                position=old.position,
                points=old.points,
            )
        )


def _copy_flows(
    db: Session,
    source_id: UUID,
    destination_id: UUID,
    actor_id: UUID,
    mapping: dict[str, dict[str, str]],
) -> None:
    for old in db.query(Flow).filter_by(course_id=source_id).all():
        new = Flow(
            id=uuid4(),
            owner_user_id=actor_id,
            course_id=destination_id,
            name=old.name,
            description=old.description,
            archived_at=None,
        )
        db.add(new)
        mapping["flows"][str(old.id)] = str(new.id)
        for old_version in old.versions:
            definition = _remap_references(
                _without_secrets(old_version.definition), mapping
            )
            pins = _remap_references(
                _without_secrets(old_version.capability_pins), mapping
            )
            config = _remap_references(
                _without_secrets(old_version.config_snapshot), mapping
            )
            new_version = FlowVersion(
                id=uuid4(),
                flow_id=new.id,
                ordinal=old_version.ordinal,
                state="draft",
                definition=definition,
                capability_pins=pins,
                config_snapshot=config,
                definition_hash=flow_version_hash(definition, pins, config),
                created_by_user_id=actor_id,
                published_at=None,
                archived_at=None,
            )
            db.add(new_version)
            mapping["flow_versions"][str(old_version.id)] = str(new_version.id)


def _copy_gradebook(
    db: Session,
    source_id: UUID,
    destination_id: UUID,
    mapping: dict[str, dict[str, str]],
) -> None:
    categories = (
        db.query(GradeCategory)
        .filter_by(course_id=source_id)
        .order_by(GradeCategory.position, GradeCategory.id)
        .all()
    )
    for old in categories:
        new = GradeCategory(
            id=uuid4(),
            course_id=destination_id,
            parent_category_id=None,
            name=old.name,
            description=old.description,
            position=old.position,
            aggregation_strategy=old.aggregation_strategy,
            weight=old.weight,
            calculation_policy=deepcopy(old.calculation_policy),
            copied_from_id=old.id,
        )
        db.add(new)
        mapping["grade_categories"][str(old.id)] = str(new.id)
    for old in categories:
        if old.parent_category_id is None:
            continue
        new_parent_id = mapping["grade_categories"].get(str(old.parent_category_id))
        if new_parent_id is not None:
            db.get(
                GradeCategory, UUID(mapping["grade_categories"][str(old.id)])
            ).parent_category_id = UUID(new_parent_id)

    for old in (
        db.query(GradeItem)
        .filter_by(course_id=source_id)
        .order_by(GradeItem.position, GradeItem.id)
        .all()
    ):
        remapped_source = None
        if old.source_type == "assignment":
            remapped_source = mapping["assignments"].get(str(old.source_id))
        elif old.source_type == "quiz":
            remapped_source = mapping["quizzes"].get(str(old.source_id))
        if old.source_type is not None and remapped_source is None:
            continue
        category_id = (
            mapping["grade_categories"].get(str(old.category_id))
            if old.category_id
            else None
        )
        new = GradeItem(
            id=uuid4(),
            course_id=destination_id,
            category_id=UUID(category_id) if category_id else None,
            title=old.title,
            description=old.description,
            position=old.position,
            max_points=old.max_points,
            weight=old.weight,
            calculation_policy=deepcopy(old.calculation_policy),
            release_policy=deepcopy(old.release_policy),
            source_type=old.source_type if remapped_source else None,
            source_id=UUID(remapped_source) if remapped_source else None,
            copied_from_id=old.id,
        )
        db.add(new)
        mapping["grade_items"][str(old.id)] = str(new.id)


def _copy_course_items(
    db: Session,
    source_id: UUID,
    destination_id: UUID,
    mapping: dict[str, dict[str, str]],
    payload: Any,
) -> None:
    next_position: dict[UUID, int] = defaultdict(int)
    items = (
        db.query(CourseItem)
        .filter_by(course_id=source_id)
        .order_by(CourseItem.section_id, CourseItem.position, CourseItem.id)
        .all()
    )
    for old in items:
        section_id = mapping["sections"].get(str(old.section_id))
        if section_id is None or not _supported_content_item(old, payload.selection):
            continue
        resource_id: UUID | None = None
        if old.resource_type == "assignment":
            mapped = mapping["assignments"].get(str(old.resource_id))
            if mapped is None:
                continue
            resource_id = UUID(mapped)
        elif old.resource_type == "quiz":
            mapped = mapping["quizzes"].get(str(old.resource_id))
            if mapped is None:
                continue
            resource_id = UUID(mapped)
        elif old.resource_type is not None:
            continue
        new_section_id = UUID(section_id)
        new = CourseItem(
            id=uuid4(),
            course_id=destination_id,
            section_id=new_section_id,
            title=old.title,
            position=next_position[new_section_id],
            kind=old.kind,
            visibility=CourseContentVisibility.draft,
            resource_type=old.resource_type,
            resource_id=resource_id,
            copied_from_id=old.id,
            payload_schema_uri=old.payload_schema_uri,
            payload=deepcopy(old.payload),
        )
        next_position[new_section_id] += 1
        db.add(new)
        mapping["items"][str(old.id)] = str(new.id)


def _remap_references(value: Any, mapping: dict[str, dict[str, str]]) -> Any:
    replacements = {
        source_id: destination_id
        for resource_mapping in mapping.values()
        for source_id, destination_id in resource_mapping.items()
    }
    if isinstance(value, dict):
        return {key: _remap_references(child, mapping) for key, child in value.items()}
    if isinstance(value, list):
        return [_remap_references(child, mapping) for child in value]
    if isinstance(value, UUID):
        replacement = replacements.get(str(value))
        return UUID(replacement) if replacement else value
    if isinstance(value, str):
        return replacements.get(value, value)
    return deepcopy(value)


__all__ = [
    "CourseCopyConflict",
    "create_or_resume_job",
    "execute",
    "preview",
    "request_fingerprint",
]
