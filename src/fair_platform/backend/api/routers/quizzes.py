from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.quiz import (
    AttemptQuestionRead,
    QuestionAuthoringRead,
    QuestionBankCreate,
    QuestionBankRead,
    QuestionCreate,
    QuestionOptionRead,
    QuestionVersionAuthoringRead,
    QuestionVersionCreate,
    QuizAnswerUpsert,
    QuizAttemptRead,
    QuizAuthoringRead,
    QuizCreate,
    QuizQuestionAdd,
    QuizQuestionAuthoringRead,
    QuizRead,
)
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.lms_quiz import (
    Question,
    QuestionBank,
    QuestionVersion,
    Quiz,
    QuizAttempt,
    QuizAttemptStatus,
)
from fair_platform.backend.data.models.user import User
from fair_platform.backend.services.course_access import (
    can_manage_course,
    can_view_course,
)
from fair_platform.backend.services.quiz_engine import (
    QuizEngineConflict,
    QuizEngineError,
    QuizEngineNotFound,
    add_quiz_question,
    attempt_questions,
    close_quiz,
    course_item_for_quiz,
    create_question,
    create_question_bank,
    create_question_version,
    create_quiz,
    get_attempt,
    get_question,
    get_question_version,
    get_quiz,
    list_attempts,
    list_question_banks,
    list_quizzes,
    publish_quiz,
    questions_for_bank,
    quiz_max_points,
    quiz_questions,
    release_attempt,
    require_learner_visible_quiz,
    save_answer,
    start_attempt,
    submit_attempt,
    versions_for_question,
)


router = APIRouter()


def _course(db: Session, course_id: UUID, user: User) -> tuple[Course, bool]:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if not can_view_course(db, course, user):
        raise HTTPException(
            status_code=403,
            detail="Only active course members can access quizzes",
        )
    return course, can_manage_course(db, course, user)


def _staff_course(db: Session, course_id: UUID, user: User, *, mutable: bool) -> Course:
    course, can_manage = _course(db, course_id, user)
    if not can_manage:
        raise HTTPException(
            status_code=403, detail="Only course staff can manage quizzes"
        )
    if mutable and course.is_archived:
        raise HTTPException(status_code=409, detail="Archived courses are read-only")
    return course


def _mutable_course(db: Session, course_id: UUID, user: User) -> tuple[Course, bool]:
    course, can_manage = _course(db, course_id, user)
    if course.is_archived:
        raise HTTPException(status_code=409, detail="Archived courses are read-only")
    return course, can_manage


def _raise_service_error(db: Session, error: Exception) -> None:
    db.rollback()
    if isinstance(error, QuizEngineNotFound):
        raise HTTPException(status_code=404, detail=str(error)) from error
    if isinstance(error, QuizEngineConflict):
        raise HTTPException(status_code=409, detail=str(error)) from error
    if isinstance(error, QuizEngineError):
        raise HTTPException(status_code=400, detail=str(error)) from error
    if isinstance(error, IntegrityError):
        raise HTTPException(
            status_code=409,
            detail="Quiz data conflicts with an existing record",
        ) from error
    raise error


def _option_reads(options: list[dict[str, str]]) -> list[QuestionOptionRead]:
    return [
        QuestionOptionRead(id=option["id"], text=option["text"]) for option in options
    ]


def _version_read(version: QuestionVersion) -> QuestionVersionAuthoringRead:
    return QuestionVersionAuthoringRead(
        id=version.id,
        question_id=version.question_id,
        version_number=version.version_number,
        kind=version.kind,
        prompt=version.prompt,
        options=_option_reads(version.options),
        correct_option_id=version.correct_option_id,
        default_points=float(version.default_points),
        explanation=version.explanation,
        created_at=version.created_at,
    )


def _question_read(db: Session, question: Question) -> QuestionAuthoringRead:
    return QuestionAuthoringRead(
        id=question.id,
        bank_id=question.bank_id,
        title=question.title,
        created_at=question.created_at,
        updated_at=question.updated_at,
        versions=[
            _version_read(version) for version in versions_for_question(db, question.id)
        ],
    )


def _bank_read(db: Session, bank: QuestionBank) -> QuestionBankRead:
    return QuestionBankRead(
        id=bank.id,
        course_id=bank.course_id,
        name=bank.name,
        description=bank.description,
        created_at=bank.created_at,
        updated_at=bank.updated_at,
        questions=[
            _question_read(db, question) for question in questions_for_bank(db, bank.id)
        ],
    )


def _quiz_read(db: Session, quiz: Quiz) -> QuizRead:
    item = course_item_for_quiz(db, quiz)
    questions = quiz_questions(db, quiz.id)
    return QuizRead(
        id=quiz.id,
        course_id=quiz.course_id,
        course_item_id=item.id,
        title=quiz.title,
        instructions=quiz.instructions,
        status=quiz.status,
        release_policy=quiz.release_policy,
        attempt_limit=quiz.attempt_limit,
        opens_at=quiz.opens_at,
        closes_at=quiz.closes_at,
        published_at=quiz.published_at,
        closed_at=quiz.closed_at,
        question_count=len(questions),
        max_points=float(quiz_max_points(db, quiz.id)),
        created_at=quiz.created_at,
        updated_at=quiz.updated_at,
    )


def _quiz_authoring_read(db: Session, quiz: Quiz) -> QuizAuthoringRead:
    summary = _quiz_read(db, quiz)
    question_reads = []
    for link in quiz_questions(db, quiz.id):
        version = get_question_version(db, quiz.course_id, link.question_version_id)
        question_reads.append(
            QuizQuestionAuthoringRead(
                id=link.id,
                position=link.position,
                points=float(link.points),
                version=_version_read(version),
            )
        )
    return QuizAuthoringRead(
        **summary.model_dump(),
        questions=question_reads,
    )


def _attempt_read(
    db: Session, attempt: QuizAttempt, *, staff_view: bool
) -> QuizAttemptRead:
    released = (
        attempt.status.value
        if hasattr(attempt.status, "value")
        else str(attempt.status)
    ) == QuizAttemptStatus.released.value
    expose_score = staff_view or released
    question_reads = []
    for attempt_question, version, answer in attempt_questions(db, attempt.id):
        question_reads.append(
            AttemptQuestionRead(
                id=attempt_question.id,
                question_version_id=version.id,
                position=attempt_question.position,
                kind=version.kind,
                prompt=version.prompt,
                options=_option_reads(version.options),
                points=float(attempt_question.points),
                selected_option_id=(answer.selected_option_id if answer else None),
                is_correct=(answer.is_correct if answer and expose_score else None),
                points_awarded=(
                    float(answer.points_awarded)
                    if answer and answer.points_awarded is not None and expose_score
                    else None
                ),
            )
        )
    return QuizAttemptRead(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        user_id=attempt.user_id,
        attempt_number=attempt.attempt_number,
        status=attempt.status,
        max_points=float(attempt.max_points),
        earned_points=(
            float(attempt.earned_points)
            if attempt.earned_points is not None and expose_score
            else None
        ),
        started_at=attempt.started_at,
        submitted_at=attempt.submitted_at,
        released_at=attempt.released_at,
        questions=question_reads,
    )


@router.get(
    "/courses/{course_id}/question-banks",
    response_model=list[QuestionBankRead],
)
def get_question_banks(
    course_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> list[QuestionBankRead]:
    _staff_course(db, course_id, current_user, mutable=False)
    return [_bank_read(db, bank) for bank in list_question_banks(db, course_id)]


@router.post(
    "/courses/{course_id}/question-banks",
    response_model=QuestionBankRead,
    status_code=status.HTTP_201_CREATED,
)
def post_question_bank(
    course_id: UUID,
    payload: QuestionBankCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> QuestionBankRead:
    _staff_course(db, course_id, current_user, mutable=True)
    try:
        bank = create_question_bank(db, course_id, **payload.model_dump())
        db.commit()
        return _bank_read(db, bank)
    except (QuizEngineError, IntegrityError) as error:
        _raise_service_error(db, error)


@router.post(
    "/courses/{course_id}/question-banks/{bank_id}/questions",
    response_model=QuestionAuthoringRead,
    status_code=status.HTTP_201_CREATED,
)
def post_question(
    course_id: UUID,
    bank_id: UUID,
    payload: QuestionCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> QuestionAuthoringRead:
    _staff_course(db, course_id, current_user, mutable=True)
    data = payload.model_dump()
    data["option_texts"] = data.pop("options")
    try:
        question, _ = create_question(db, course_id, bank_id, current_user, **data)
        db.commit()
        return _question_read(db, question)
    except (QuizEngineError, IntegrityError) as error:
        _raise_service_error(db, error)


@router.post(
    "/courses/{course_id}/questions/{question_id}/versions",
    response_model=QuestionAuthoringRead,
    status_code=status.HTTP_201_CREATED,
)
def post_question_version(
    course_id: UUID,
    question_id: UUID,
    payload: QuestionVersionCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> QuestionAuthoringRead:
    _staff_course(db, course_id, current_user, mutable=True)
    data = payload.model_dump()
    data["option_texts"] = data.pop("options")
    try:
        create_question_version(db, course_id, question_id, current_user, **data)
        question = get_question(db, course_id, question_id)
        db.commit()
        return _question_read(db, question)
    except (QuizEngineError, IntegrityError) as error:
        _raise_service_error(db, error)


@router.get("/courses/{course_id}/quizzes", response_model=list[QuizRead])
def get_quizzes(
    course_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> list[QuizRead]:
    _, staff_view = _course(db, course_id, current_user)
    return [
        _quiz_read(db, quiz)
        for quiz in list_quizzes(db, course_id, staff_view=staff_view)
    ]


@router.post(
    "/courses/{course_id}/quizzes",
    response_model=QuizAuthoringRead,
    status_code=status.HTTP_201_CREATED,
)
def post_quiz(
    course_id: UUID,
    payload: QuizCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> QuizAuthoringRead:
    _staff_course(db, course_id, current_user, mutable=True)
    try:
        quiz = create_quiz(
            db,
            course_id,
            payload.section_id,
            current_user,
            **payload.model_dump(exclude={"section_id"}),
        )
        db.commit()
        return _quiz_authoring_read(db, quiz)
    except (QuizEngineError, IntegrityError) as error:
        _raise_service_error(db, error)


@router.get("/courses/{course_id}/quizzes/{quiz_id}", response_model=QuizRead)
def get_quiz_summary(
    course_id: UUID,
    quiz_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> QuizRead:
    _, staff_view = _course(db, course_id, current_user)
    try:
        quiz = get_quiz(db, course_id, quiz_id)
        if not staff_view:
            require_learner_visible_quiz(db, quiz)
        return _quiz_read(db, quiz)
    except QuizEngineError as error:
        _raise_service_error(db, error)


@router.get(
    "/courses/{course_id}/quizzes/{quiz_id}/authoring",
    response_model=QuizAuthoringRead,
)
def get_quiz_authoring(
    course_id: UUID,
    quiz_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> QuizAuthoringRead:
    _staff_course(db, course_id, current_user, mutable=False)
    try:
        return _quiz_authoring_read(db, get_quiz(db, course_id, quiz_id))
    except QuizEngineError as error:
        _raise_service_error(db, error)


@router.post(
    "/courses/{course_id}/quizzes/{quiz_id}/questions",
    response_model=QuizAuthoringRead,
    status_code=status.HTTP_201_CREATED,
)
def post_quiz_question(
    course_id: UUID,
    quiz_id: UUID,
    payload: QuizQuestionAdd,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> QuizAuthoringRead:
    _staff_course(db, course_id, current_user, mutable=True)
    try:
        quiz = get_quiz(db, course_id, quiz_id)
        add_quiz_question(
            db,
            quiz,
            question_version_id=payload.question_version_id,
            points=payload.points,
        )
        db.commit()
        return _quiz_authoring_read(db, quiz)
    except (QuizEngineError, IntegrityError) as error:
        _raise_service_error(db, error)


@router.post(
    "/courses/{course_id}/quizzes/{quiz_id}/publish",
    response_model=QuizAuthoringRead,
)
def post_publish_quiz(
    course_id: UUID,
    quiz_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> QuizAuthoringRead:
    _staff_course(db, course_id, current_user, mutable=True)
    try:
        quiz = publish_quiz(db, get_quiz(db, course_id, quiz_id))
        db.commit()
        return _quiz_authoring_read(db, quiz)
    except (QuizEngineError, IntegrityError) as error:
        _raise_service_error(db, error)


@router.post(
    "/courses/{course_id}/quizzes/{quiz_id}/close",
    response_model=QuizAuthoringRead,
)
def post_close_quiz(
    course_id: UUID,
    quiz_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> QuizAuthoringRead:
    _staff_course(db, course_id, current_user, mutable=True)
    try:
        quiz = close_quiz(db, get_quiz(db, course_id, quiz_id))
        db.commit()
        return _quiz_authoring_read(db, quiz)
    except QuizEngineError as error:
        _raise_service_error(db, error)


@router.get(
    "/courses/{course_id}/quizzes/{quiz_id}/attempts",
    response_model=list[QuizAttemptRead],
)
def get_quiz_attempts(
    course_id: UUID,
    quiz_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> list[QuizAttemptRead]:
    _, staff_view = _course(db, course_id, current_user)
    try:
        quiz = get_quiz(db, course_id, quiz_id)
        if not staff_view:
            require_learner_visible_quiz(db, quiz)
        attempts = list_attempts(
            db, quiz, user_id=None if staff_view else current_user.id
        )
        return [
            _attempt_read(db, attempt, staff_view=staff_view) for attempt in attempts
        ]
    except QuizEngineError as error:
        _raise_service_error(db, error)


@router.post(
    "/courses/{course_id}/quizzes/{quiz_id}/attempts",
    response_model=QuizAttemptRead,
    status_code=status.HTTP_201_CREATED,
)
def post_quiz_attempt(
    course_id: UUID,
    quiz_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> QuizAttemptRead:
    _, staff_view = _mutable_course(db, course_id, current_user)
    if staff_view:
        raise HTTPException(
            status_code=403, detail="Course staff cannot take learner quizzes"
        )
    try:
        quiz = get_quiz(db, course_id, quiz_id)
        attempt = start_attempt(db, quiz, current_user)
        db.commit()
        return _attempt_read(db, attempt, staff_view=False)
    except (QuizEngineError, IntegrityError) as error:
        _raise_service_error(db, error)


@router.get(
    "/courses/{course_id}/quizzes/{quiz_id}/attempts/{attempt_id}",
    response_model=QuizAttemptRead,
)
def get_quiz_attempt(
    course_id: UUID,
    quiz_id: UUID,
    attempt_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> QuizAttemptRead:
    _, staff_view = _course(db, course_id, current_user)
    try:
        quiz = get_quiz(db, course_id, quiz_id)
        attempt = get_attempt(db, course_id, attempt_id)
        if attempt.quiz_id != quiz.id or (
            not staff_view and attempt.user_id != current_user.id
        ):
            raise QuizEngineNotFound("Quiz attempt not found")
        return _attempt_read(db, attempt, staff_view=staff_view)
    except QuizEngineError as error:
        _raise_service_error(db, error)


@router.put(
    "/courses/{course_id}/quizzes/{quiz_id}/attempts/{attempt_id}/answers/{attempt_question_id}",
    response_model=QuizAttemptRead,
)
def put_quiz_answer(
    course_id: UUID,
    quiz_id: UUID,
    attempt_id: UUID,
    attempt_question_id: UUID,
    payload: QuizAnswerUpsert,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> QuizAttemptRead:
    _, staff_view = _mutable_course(db, course_id, current_user)
    if staff_view:
        raise HTTPException(
            status_code=403, detail="Course staff cannot answer learner quizzes"
        )
    try:
        quiz = get_quiz(db, course_id, quiz_id)
        attempt = get_attempt(db, course_id, attempt_id)
        save_answer(
            db,
            quiz,
            attempt,
            current_user,
            attempt_question_id=attempt_question_id,
            selected_option_id=payload.selected_option_id,
        )
        db.commit()
        return _attempt_read(db, attempt, staff_view=False)
    except (QuizEngineError, IntegrityError) as error:
        _raise_service_error(db, error)


@router.post(
    "/courses/{course_id}/quizzes/{quiz_id}/attempts/{attempt_id}/submit",
    response_model=QuizAttemptRead,
)
def post_submit_attempt(
    course_id: UUID,
    quiz_id: UUID,
    attempt_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> QuizAttemptRead:
    _, staff_view = _mutable_course(db, course_id, current_user)
    if staff_view:
        raise HTTPException(
            status_code=403, detail="Course staff cannot submit learner quizzes"
        )
    try:
        quiz = get_quiz(db, course_id, quiz_id)
        attempt = submit_attempt(
            db, quiz, get_attempt(db, course_id, attempt_id), current_user
        )
        db.commit()
        return _attempt_read(db, attempt, staff_view=False)
    except (QuizEngineError, IntegrityError) as error:
        _raise_service_error(db, error)


@router.post(
    "/courses/{course_id}/quizzes/{quiz_id}/attempts/{attempt_id}/release",
    response_model=QuizAttemptRead,
)
def post_release_attempt(
    course_id: UUID,
    quiz_id: UUID,
    attempt_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> QuizAttemptRead:
    _staff_course(db, course_id, current_user, mutable=True)
    try:
        quiz = get_quiz(db, course_id, quiz_id)
        attempt = release_attempt(
            db,
            quiz,
            get_attempt(db, course_id, attempt_id),
            actor=current_user,
        )
        db.commit()
        return _attempt_read(db, attempt, staff_view=True)
    except (QuizEngineError, IntegrityError) as error:
        _raise_service_error(db, error)


__all__ = ["router"]
