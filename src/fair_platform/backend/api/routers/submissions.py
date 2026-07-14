from uuid import UUID, uuid4
from typing import List, Optional
from datetime import datetime, timezone
import json

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.submission import (
    Submission,
    SubmissionStatus,
    submission_artifacts,
)
from fair_platform.backend.data.models.submitter import Submitter
from fair_platform.backend.data.models.assignment import Assignment, AssignmentStatus
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.user import User
from fair_platform.backend.data.models.artifact import Artifact, ArtifactStatus, AccessLevel
from fair_platform.backend.api.schema.submission import (
    SubmissionRead,
    SubmissionUpdate,
    SubmissionDraftUpdate,
)
from fair_platform.backend.api.schema.submission_event import SubmissionTimelineEventRead
from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.services.artifact_manager import get_artifact_manager
from fair_platform.backend.services.submission_manager import get_submission_manager
from fair_platform.backend.data.models.submission_event import SubmissionEvent
from fair_platform.backend.core.security.permissions import has_capability
from fair_platform.backend.data.models.enrollment import (
    CourseMembershipRole,
    Enrollment,
    EnrollmentStatus,
)
from fair_platform.backend.services.course_access import active_membership, can_manage_course
from fair_platform.backend.data.models.lms_communication import Notification

router = APIRouter()


@router.post("/", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
@router.post("/synthetic", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
async def create_submission(
    assignment_id: UUID = Form(...),
    submitter_name: Optional[str] = Form(None),
    artifact_ids: str = Form(None),
    files: List[UploadFile] = File(None),
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    """
    Create a submission with optional file uploads and/or existing artifact references.

    This endpoint supports both multipart/form-data (for file uploads) and can reference
    existing artifacts by ID. All operations are atomic - if any step fails, everything
    is rolled back.

    Form fields:
    - assignment_id: UUID of the assignment (required)
    - submitter_name: Name of the submitter (required)
    - artifact_ids: Optional JSON array of existing artifact UUIDs: ["uuid1", "uuid2"]
    - files: Optional list of files to upload as new artifacts
    """
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
        )

    course = db.get(Course, assignment.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    is_staff_submission = can_manage_course(db, course, current_user)
    membership = active_membership(db, course.id, current_user.id)
    is_student_submission = bool(
        membership
        and membership.role == CourseMembershipRole.student
        and assignment.status == AssignmentStatus.published
        and not course.is_archived
    )
    if not is_staff_submission and not is_student_submission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only course staff or an enrolled student can submit this assignment",
        )


    try:
        existing_artifact_ids = []
        if artifact_ids:
            try:
                existing_artifact_ids = json.loads(artifact_ids)
                if not isinstance(existing_artifact_ids, list):
                    raise ValueError("artifact_ids must be an array")
            except (json.JSONDecodeError, ValueError) as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid artifact_ids JSON. Expected array of UUIDs: {str(e)}"
                )

        if is_staff_submission:
            if not submitter_name or not submitter_name.strip():
                raise HTTPException(status_code=422, detail="A synthetic submitter name is required")
            submitter = Submitter(
                id=uuid4(),
                name=submitter_name.strip(),
                email=None,
                user_id=None,
                is_synthetic=True,
                created_at=datetime.now(timezone.utc),
            )
            db.add(submitter)
            db.flush()
        else:
            submitter = db.query(Submitter).filter(Submitter.user_id == current_user.id).first()
            if submitter is None:
                submitter = Submitter(
                    id=uuid4(),
                    name=current_user.name,
                    email=str(current_user.email),
                    user_id=current_user.id,
                    is_synthetic=False,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(submitter)
                db.flush()

        previous_attempt = (
            db.query(Submission)
            .filter(
                Submission.assignment_id == assignment_id,
                Submission.submitter_id == submitter.id,
            )
            .order_by(Submission.attempt_number.desc())
            .first()
        )
        if previous_attempt and not assignment.allow_resubmissions:
            raise HTTPException(status_code=409, detail="This assignment does not allow resubmissions")
        attempt_number = (previous_attempt.attempt_number + 1) if previous_attempt else 1
        submitted_at = datetime.now(timezone.utc)

        sub = Submission(
            id=uuid4(),
            assignment_id=assignment_id,
            submitter_id=submitter.id,
            created_by_id=current_user.id,  # Track who created this submission
            submitted_at=submitted_at,
            status=SubmissionStatus.submitted,
            attempt_number=attempt_number,
            is_late=bool(assignment.deadline and submitted_at.replace(tzinfo=None) > assignment.deadline.replace(tzinfo=None)),
        )
        db.add(sub)
        db.flush()

        manager = get_artifact_manager(db)

        if existing_artifact_ids:
            for artifact_id in existing_artifact_ids:
                try:
                    manager.attach_to_submission(UUID(artifact_id), sub.id, current_user)
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid artifact ID format: {artifact_id}"
                    )

        if files:
            for file in files:
                artifact = manager.create_artifact(
                    file=file,
                    creator=current_user,
                    status=ArtifactStatus.attached,
                    access_level=AccessLevel.private,
                    course_id=assignment.course_id,
                )
                sub.artifacts.append(artifact)

        sub_mgr = get_submission_manager(db)
        sub_mgr.log_submission_submitted(
            submission=sub,
            actor=current_user,
            artifact_count=len(sub.artifacts),
        )

        db.commit()
        db.refresh(sub)
        return sub

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create submission: {str(e)}"
        )


@router.get("/", response_model=List[SubmissionRead])
def list_submissions(
    db: Session = Depends(session_dependency),
    assignment_id: UUID = Query(None, description="Filter submissions by assignment ID"),
    current_user: User = Depends(get_current_user),
):
    """List all submissions, optionally filtered by assignment ID."""
    query = db.query(Submission)

    if has_capability(current_user, "view_all_submissions"):
        pass
    else:
        query = (
            query.join(Assignment, Submission.assignment_id == Assignment.id)
            .join(Course, Assignment.course_id == Course.id)
            .join(Submitter, Submission.submitter_id == Submitter.id)
            .outerjoin(
                Enrollment,
                and_(
                    Enrollment.course_id == Course.id,
                    Enrollment.user_id == current_user.id,
                    Enrollment.status == EnrollmentStatus.active,
                ),
            )
            .filter(
                or_(
                    Course.instructor_id == current_user.id,
                    Enrollment.role == CourseMembershipRole.assistant,
                    Submitter.user_id == current_user.id,
                )
            )
        )

    if assignment_id is not None:
        if not db.get(Assignment, assignment_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
            )
        query = query.filter(Submission.assignment_id == assignment_id)

    submissions = query.all()


    # Fetch all submitters in one query to avoid N+1
    submitter_ids = [sub.submitter_id for sub in submissions]
    submitters = db.query(Submitter).filter(Submitter.id.in_(submitter_ids)).all()
    submitter_map = {submitter.id: submitter for submitter in submitters}

    # Manually construct response with submitter data
    result = []
    for sub in submissions:
        sub_dict = {
            "id": sub.id,
            "assignment_id": sub.assignment_id,
            "submitter_id": sub.submitter_id,
            "created_by_id": sub.created_by_id,
            "submitter": submitter_map.get(sub.submitter_id),
            "submitted_at": sub.submitted_at,
            "status": sub.status,
            "artifacts": sub.artifacts,
            "draft_score": sub.draft_score,
            "draft_feedback": sub.draft_feedback,
            "published_score": sub.published_score,
            "published_feedback": sub.published_feedback,
            "returned_at": sub.returned_at,
            "attempt_number": sub.attempt_number,
            "is_late": sub.is_late,
        }

        assignment = db.get(Assignment, sub.assignment_id)
        course = db.get(Course, assignment.course_id) if assignment else None
        manages_submission = bool(course and can_manage_course(db, course, current_user))
        if not manages_submission:
            sub_dict["draft_score"] = None
            sub_dict["draft_feedback"] = None
        result.append(sub_dict)

    return result



@router.get("/{submission_id}", response_model=SubmissionRead)
def get_submission(
    submission_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):

    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )

    assignment = db.get(Assignment, sub.assignment_id)
    course = db.get(Course, assignment.course_id) if assignment else None
    can_manage = bool(course and can_manage_course(db, course, current_user))
    submitter = db.get(Submitter, sub.submitter_id)
    if not has_capability(current_user, "view_all_submissions"):
        if not can_manage and (not submitter or submitter.user_id != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this submission",
            )

    response = {
        "id": sub.id,
        "assignment_id": sub.assignment_id,
        "submitter_id": sub.submitter_id,
        "created_by_id": sub.created_by_id,
        "submitter": submitter,
        "submitted_at": sub.submitted_at,
        "status": sub.status,
        "artifacts": sub.artifacts,
        "draft_score": sub.draft_score if can_manage else None,
        "draft_feedback": sub.draft_feedback if can_manage else None,
        "published_score": sub.published_score,
        "published_feedback": sub.published_feedback,
        "returned_at": sub.returned_at,
        "attempt_number": sub.attempt_number,
        "is_late": sub.is_late,
    }

    return response


@router.put("/{submission_id}", response_model=SubmissionRead)
def update_submission(
    submission_id: UUID,
    payload: SubmissionUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )


    assignment = db.get(Assignment, sub.assignment_id)
    course = db.get(Course, assignment.course_id) if assignment else None
    if not course or not can_manage_course(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can update this submission",
        )

    if payload.artifact_ids is not None:
        manager = get_artifact_manager(db)

        old_artifacts = db.query(Artifact).join(
            submission_artifacts,
            submission_artifacts.c.artifact_id == Artifact.id
        ).filter(
            submission_artifacts.c.submission_id == sub.id
        ).all()

        for artifact in old_artifacts:
            manager.detach_from_submission(artifact.id, sub.id, current_user)

        for aid in payload.artifact_ids:
            manager.attach_to_submission(aid, sub.id, current_user)

        db.commit()

    db.refresh(sub)
    return sub


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_submission(
    submission_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )


    assignment = db.get(Assignment, sub.assignment_id)
    course = db.get(Course, assignment.course_id) if assignment else None
    if not course or not can_manage_course(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can delete this submission",
        )


    db.delete(sub)
    db.commit()
    return None


@router.patch("/{submission_id}/draft", response_model=SubmissionRead)
def update_submission_draft(
    submission_id: UUID,
    payload: SubmissionDraftUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )

    assignment = db.get(Assignment, sub.assignment_id)
    course = db.get(Course, assignment.course_id) if assignment else None
    if not course or not can_manage_course(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can edit drafts",
        )

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide score and/or feedback to update",
        )

    try:
        mgr = get_submission_manager(db)
        mgr.update_draft(
            submission_id=sub.id,
            score=data.get("score"),
            feedback=data.get("feedback"),
            actor=current_user,
        )
        db.commit()
        db.refresh(sub)
        return sub
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update draft: {str(e)}",
        )


@router.post("/{submission_id}/return", response_model=SubmissionRead)
def return_submission(
    submission_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )

    assignment = db.get(Assignment, sub.assignment_id)
    course = db.get(Course, assignment.course_id) if assignment else None
    if not course or not can_manage_course(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can return submissions",
        )

    try:
        mgr = get_submission_manager(db)
        mgr.return_to_student(submission_id=sub.id, actor=current_user)
        submitter = db.get(Submitter, sub.submitter_id)
        if submitter and submitter.user_id:
            db.add(
                Notification(
                    id=uuid4(),
                    user_id=submitter.user_id,
                    kind="grade_returned",
                    title=f"Grade returned: {assignment.title}",
                    body=sub.published_feedback,
                    link=f"/courses/{course.id}/assignments/{assignment.id}",
                )
            )
        db.commit()
        db.refresh(sub)
        return sub
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to return submission: {str(e)}",
        )


@router.get("/{submission_id}/timeline", response_model=List[SubmissionTimelineEventRead])
def get_submission_timeline(
    submission_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found"
        )

    assignment = db.get(Assignment, sub.assignment_id)
    course = db.get(Course, assignment.course_id) if assignment else None
    if not course or not can_manage_course(db, course, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this submission's timeline",
        )

    events = (
        db.query(SubmissionEvent)
        .filter(SubmissionEvent.submission_id == submission_id)
        .options(
            joinedload(SubmissionEvent.actor),
            joinedload(SubmissionEvent.execution),
        )
        .order_by(SubmissionEvent.created_at)
        .all()
    )
    return events


__all__ = ["router"]
