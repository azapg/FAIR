from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.lms import (
    CourseGradebook,
    GradebookAssignment,
    GradebookCell,
    GradebookRow,
    GradingQueueItem,
    StudentTodoItem,
)
from fair_platform.backend.api.schema.lms_communication import (
    CourseCommentCreate,
    CourseCommentRead,
    CoursePostCreate,
    CoursePostRead,
    NotificationRead,
    SubmissionCommentCreate,
    SubmissionCommentRead,
)
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.assignment import Assignment, AssignmentStatus
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.enrollment import (
    CourseMembershipRole,
    Enrollment,
    EnrollmentStatus,
)
from fair_platform.backend.data.models.submission import Submission, SubmissionStatus
from fair_platform.backend.data.models.submitter import Submitter
from fair_platform.backend.data.models.user import User
from fair_platform.backend.data.models.artifact import AccessLevel, Artifact
from fair_platform.backend.data.models.lms_communication import (
    CourseComment,
    CoursePost,
    Notification,
    SubmissionComment,
)
from fair_platform.backend.services.course_access import can_manage_course, can_view_course
from fair_platform.backend.services.notifications import notify_course_members


router = APIRouter()


def _managed_course(db: Session, course_id: UUID, user: User) -> Course:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not can_manage_course(db, course, user):
        raise HTTPException(status_code=403, detail="Only course staff can view grading data")
    return course


def _viewable_course(db: Session, course_id: UUID, user: User) -> Course:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if not can_view_course(db, course, user):
        raise HTTPException(status_code=403, detail="Only active course members can view this course")
    return course


def _post_read(post: CoursePost) -> CoursePostRead:
    return CoursePostRead(
        id=post.id,
        course_id=post.course_id,
        author_id=post.author_id,
        author_name=post.author.name,
        kind=post.kind,
        title=post.title,
        body=post.body,
        artifacts=post.artifacts,
        comments_count=len(post.comments),
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


def _submission_context(db: Session, submission_id: UUID, user: User):
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    submitter = db.get(Submitter, submission.submitter_id)
    assignment = db.get(Assignment, submission.assignment_id)
    course = db.get(Course, assignment.course_id) if assignment else None
    if not assignment or not course or not submitter:
        raise HTTPException(status_code=404, detail="Submission context not found")
    if not can_manage_course(db, course, user) and submitter.user_id != user.id:
        raise HTTPException(status_code=403, detail="Submission comments are private")
    return submission, submitter, assignment, course


def _course_grading_data(db: Session, course_id: UUID):
    assignments = (
        db.query(Assignment)
        .filter(
            Assignment.course_id == course_id,
            Assignment.status.in_([AssignmentStatus.published, AssignmentStatus.closed]),
        )
        .order_by(Assignment.deadline, Assignment.title)
        .all()
    )
    memberships = (
        db.query(Enrollment)
        .filter(
            Enrollment.course_id == course_id,
            Enrollment.role == CourseMembershipRole.student,
            Enrollment.status == EnrollmentStatus.active,
        )
        .all()
    )
    users = {
        user.id: user
        for user in db.query(User).filter(User.id.in_([item.user_id for item in memberships])).all()
    }
    submitters = {
        item.user_id: item
        for item in db.query(Submitter)
        .filter(Submitter.user_id.in_(users.keys()), Submitter.is_synthetic.is_(False))
        .all()
    }
    submissions = (
        db.query(Submission)
        .filter(Submission.assignment_id.in_([item.id for item in assignments]))
        .order_by(Submission.attempt_number)
        .all()
    )
    by_student_assignment: dict[tuple[UUID, UUID], list[Submission]] = {}
    submitter_users = {item.id: user_id for user_id, item in submitters.items()}
    for submission in submissions:
        user_id = submitter_users.get(submission.submitter_id)
        if user_id is not None:
            by_student_assignment.setdefault((user_id, submission.assignment_id), []).append(submission)
    return assignments, memberships, users, by_student_assignment


@router.get("/courses/{course_id}/gradebook", response_model=CourseGradebook)
def get_course_gradebook(
    course_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    _managed_course(db, course_id, current_user)
    assignments, memberships, users, attempts = _course_grading_data(db, course_id)
    rows: list[GradebookRow] = []
    for membership in memberships:
        user = users.get(membership.user_id)
        if not user:
            continue
        cells: list[GradebookCell] = []
        for assignment in assignments:
            student_attempts = attempts.get((user.id, assignment.id), [])
            latest = student_attempts[-1] if student_attempts else None
            if latest is None:
                state = "missing"
            elif latest.status == SubmissionStatus.returned:
                state = "returned"
            elif latest.status == SubmissionStatus.excused:
                state = "excused"
            else:
                state = "submitted"
            cells.append(
                GradebookCell(
                    assignment_id=assignment.id,
                    state=state,
                    submission_id=latest.id if latest else None,
                    score=latest.published_score if latest and state == "returned" else None,
                    submitted_at=latest.submitted_at if latest else None,
                    is_late=latest.is_late if latest else False,
                    attempt_count=len(student_attempts),
                )
            )
        rows.append(
            GradebookRow(
                user_id=user.id,
                name=user.name,
                email=str(user.email),
                cells=cells,
            )
        )
    return CourseGradebook(
        course_id=course_id,
        assignments=[GradebookAssignment.model_validate(item) for item in assignments],
        rows=rows,
    )


@router.get("/courses/{course_id}/grading-queue", response_model=list[GradingQueueItem])
def get_grading_queue(
    course_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    _managed_course(db, course_id, current_user)
    assignments, memberships, users, attempts = _course_grading_data(db, course_id)
    assignment_map = {item.id: item for item in assignments}
    items: list[GradingQueueItem] = []
    for membership in memberships:
        user = users.get(membership.user_id)
        if not user:
            continue
        for assignment in assignments:
            student_attempts = attempts.get((user.id, assignment.id), [])
            if not student_attempts:
                continue
            latest = student_attempts[-1]
            if latest.status in {SubmissionStatus.returned, SubmissionStatus.excused}:
                continue
            items.append(
                GradingQueueItem(
                    submission_id=latest.id,
                    assignment_id=latest.assignment_id,
                    assignment_title=assignment_map[latest.assignment_id].title,
                    user_id=user.id,
                    student_name=user.name,
                    submitted_at=latest.submitted_at,
                    is_late=latest.is_late,
                    attempt_number=latest.attempt_number,
                    status=latest.status.value if isinstance(latest.status, SubmissionStatus) else latest.status,
                )
            )
    return sorted(items, key=lambda item: item.submitted_at.isoformat() if item.submitted_at else "")


@router.get("/todo", response_model=list[StudentTodoItem])
def get_student_todo(
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    courses = (
        db.query(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(
            Enrollment.user_id == current_user.id,
            Enrollment.role == CourseMembershipRole.student,
            Enrollment.status == EnrollmentStatus.active,
            Course.is_archived.is_(False),
        )
        .all()
    )
    course_map = {course.id: course for course in courses}
    assignments = (
        db.query(Assignment)
        .filter(
            Assignment.course_id.in_(course_map),
            Assignment.status == AssignmentStatus.published,
        )
        .order_by(Assignment.deadline, Assignment.title)
        .all()
    )
    submitter = (
        db.query(Submitter)
        .filter(Submitter.user_id == current_user.id, Submitter.is_synthetic.is_(False))
        .first()
    )
    submissions = (
        db.query(Submission)
        .filter(
            Submission.assignment_id.in_([assignment.id for assignment in assignments]),
            Submission.submitter_id == submitter.id,
        )
        .order_by(Submission.attempt_number)
        .all()
        if submitter
        else []
    )
    attempts: dict[UUID, list[Submission]] = {}
    for submission in submissions:
        attempts.setdefault(submission.assignment_id, []).append(submission)
    items: list[StudentTodoItem] = []
    for assignment in assignments:
        assignment_attempts = attempts.get(assignment.id, [])
        latest = assignment_attempts[-1] if assignment_attempts else None
        if latest and latest.status in {SubmissionStatus.returned, SubmissionStatus.excused}:
            continue
        items.append(
            StudentTodoItem(
                assignment_id=assignment.id,
                assignment_title=assignment.title,
                course_id=assignment.course_id,
                course_name=course_map[assignment.course_id].name,
                deadline=assignment.deadline,
                state="submitted" if latest else "missing",
                submission_id=latest.id if latest else None,
                attempt_count=len(assignment_attempts),
                is_late=latest.is_late if latest else False,
            )
        )
    return items


@router.get(
    "/submissions/{submission_id}/comments", response_model=list[SubmissionCommentRead]
)
def list_submission_comments(
    submission_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    _submission_context(db, submission_id, current_user)
    comments = (
        db.query(SubmissionComment)
        .filter(SubmissionComment.submission_id == submission_id)
        .order_by(SubmissionComment.created_at)
        .all()
    )
    return [
        SubmissionCommentRead(
            id=comment.id,
            submission_id=comment.submission_id,
            author_id=comment.author_id,
            author_name=comment.author.name,
            body=comment.body,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )
        for comment in comments
    ]


@router.post(
    "/submissions/{submission_id}/comments",
    response_model=SubmissionCommentRead,
    status_code=201,
)
def create_submission_comment(
    submission_id: UUID,
    payload: SubmissionCommentCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    _submission, submitter, assignment, course = _submission_context(
        db, submission_id, current_user
    )
    comment = SubmissionComment(
        id=uuid4(),
        submission_id=submission_id,
        author_id=current_user.id,
        body=payload.body.strip(),
    )
    db.add(comment)
    recipient_id = (
        submitter.user_id
        if can_manage_course(db, course, current_user)
        else course.instructor_id
    )
    if recipient_id and recipient_id != current_user.id:
        db.add(
            Notification(
                id=uuid4(),
                user_id=recipient_id,
                kind="submission_comment",
                title=f"Private comment: {assignment.title}",
                body=comment.body,
                link=f"/courses/{course.id}/assignments/{assignment.id}",
            )
        )
    db.commit()
    db.refresh(comment)
    return SubmissionCommentRead(
        id=comment.id,
        submission_id=comment.submission_id,
        author_id=comment.author_id,
        author_name=current_user.name,
        body=comment.body,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.get("/courses/{course_id}/posts", response_model=list[CoursePostRead])
def list_course_posts(
    course_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    _viewable_course(db, course_id, current_user)
    posts = (
        db.query(CoursePost)
        .filter(CoursePost.course_id == course_id)
        .order_by(CoursePost.created_at.desc())
        .all()
    )
    return [_post_read(post) for post in posts]


@router.post("/courses/{course_id}/posts", response_model=CoursePostRead, status_code=201)
def create_course_post(
    course_id: UUID,
    payload: CoursePostCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    course = _managed_course(db, course_id, current_user)
    if course.is_archived:
        raise HTTPException(status_code=400, detail="Archived courses are read-only")
    artifacts = (
        db.query(Artifact).filter(Artifact.id.in_(payload.artifact_ids)).all()
        if payload.artifact_ids
        else []
    )
    if len(artifacts) != len(set(payload.artifact_ids)) or any(
        artifact.course_id != course_id
        or artifact.access_level not in {AccessLevel.course, AccessLevel.public}
        for artifact in artifacts
    ):
        raise HTTPException(status_code=400, detail="Post artifacts must be course-visible artifacts from this course")
    post = CoursePost(
        id=uuid4(),
        course_id=course_id,
        author_id=current_user.id,
        kind=payload.kind,
        title=payload.title.strip(),
        body=payload.body,
        artifacts=artifacts,
    )
    db.add(post)
    db.flush()
    notify_course_members(
        db,
        course_id=course_id,
        kind="course_post",
        title=post.title,
        body=post.body,
        link=f"/courses/{course_id}/stream",
        exclude_user_id=current_user.id,
    )
    db.commit()
    db.refresh(post)
    return _post_read(post)


@router.delete("/posts/{post_id}", status_code=204)
def delete_course_post(
    post_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    post = db.get(CoursePost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    course = db.get(Course, post.course_id)
    if not course or (post.author_id != current_user.id and not can_manage_course(db, course, current_user)):
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    db.delete(post)
    db.commit()


@router.get("/posts/{post_id}/comments", response_model=list[CourseCommentRead])
def list_post_comments(
    post_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    post = db.get(CoursePost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    _viewable_course(db, post.course_id, current_user)
    comments = (
        db.query(CourseComment)
        .filter(CourseComment.post_id == post_id)
        .order_by(CourseComment.created_at)
        .all()
    )
    return [
        CourseCommentRead(
            id=comment.id,
            post_id=comment.post_id,
            author_id=comment.author_id,
            author_name=comment.author.name,
            body=comment.body,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )
        for comment in comments
    ]


@router.post("/posts/{post_id}/comments", response_model=CourseCommentRead, status_code=201)
def create_post_comment(
    post_id: UUID,
    payload: CourseCommentCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    post = db.get(CoursePost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    course = _viewable_course(db, post.course_id, current_user)
    if course.is_archived:
        raise HTTPException(status_code=400, detail="Archived courses are read-only")
    comment = CourseComment(
        id=uuid4(), post_id=post.id, author_id=current_user.id, body=payload.body.strip()
    )
    db.add(comment)
    if post.author_id != current_user.id:
        db.add(
            Notification(
                id=uuid4(),
                user_id=post.author_id,
                kind="course_comment",
                title=f"New comment on {post.title}",
                body=comment.body,
                link=f"/courses/{post.course_id}/stream",
            )
        )
    db.commit()
    db.refresh(comment)
    return CourseCommentRead(
        id=comment.id,
        post_id=comment.post_id,
        author_id=comment.author_id,
        author_name=current_user.name,
        body=comment.body,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.get("/notifications", response_model=list[NotificationRead])
def list_notifications(
    unread_only: bool = Query(False),
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        query = query.filter(Notification.read_at.is_(None))
    return query.order_by(Notification.created_at.desc()).limit(100).all()


@router.post("/notifications/read-all", status_code=204)
def read_all_notifications(
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.read_at.is_(None)
    ).update({Notification.read_at: datetime.utcnow()}, synchronize_session=False)
    db.commit()


@router.post("/notifications/{notification_id}/read", response_model=NotificationRead)
def read_notification(
    notification_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    notification = db.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to read this notification")
    notification.read_at = notification.read_at or datetime.utcnow()
    db.commit()
    db.refresh(notification)
    return notification


__all__ = ["router"]
