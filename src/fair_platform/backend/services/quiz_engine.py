from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from threading import Lock, RLock
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import event, func
from sqlalchemy.orm import Session

from fair_platform.backend.data.models.enrollment import (
    CourseMembershipRole,
    Enrollment,
    EnrollmentStatus,
)
from fair_platform.backend.data.models.lms_content import (
    CourseContentVisibility,
    CourseItem,
    CourseSection,
)
from fair_platform.backend.data.models.lms_gradebook import (
    GradeEntry,
    GradeEntryStatus,
    GradeItem,
    GradeReleaseState,
)
from fair_platform.backend.data.models.lms_quiz import (
    Question,
    QuestionBank,
    QuestionKind,
    QuestionVersion,
    Quiz,
    QuizAnswer,
    QuizAttempt,
    QuizAttemptQuestion,
    QuizAttemptStatus,
    QuizQuestion,
    QuizReleasePolicy,
    QuizStatus,
)
from fair_platform.backend.data.models.user import User
from fair_platform.backend.services.course_content_service import CourseContentService
from fair_platform.backend.services.gradebook import ensure_default_category


QUIZ_GRADE_ITEM_SOURCE_TYPE = "quiz"
QUIZ_ATTEMPT_ENTRY_SOURCE_TYPE = "quiz_attempt"
_SQLITE_ATTEMPT_LOCKS: dict[UUID, RLock] = {}
_SQLITE_ATTEMPT_LOCKS_GUARD = Lock()
_SESSION_ATTEMPT_LOCKS_KEY = "fair_quiz_attempt_locks"
_SQLITE_QUIZ_LOCKS: dict[UUID, RLock] = {}
_SQLITE_QUIZ_LOCKS_GUARD = Lock()
_SESSION_QUIZ_LOCKS_KEY = "fair_quiz_locks"


class QuizEngineError(ValueError):
    pass


class QuizEngineNotFound(QuizEngineError):
    pass


class QuizEngineConflict(QuizEngineError):
    pass


def _release_sqlite_attempt_locks(session: Session, transaction: Any) -> None:
    if transaction.parent is not None:
        return
    locks = session.info.pop(_SESSION_ATTEMPT_LOCKS_KEY, {})
    for lock in reversed(list(locks.values())):
        lock.release()
    quiz_locks = session.info.pop(_SESSION_QUIZ_LOCKS_KEY, {})
    for lock in reversed(list(quiz_locks.values())):
        lock.release()


event.listen(Session, "after_transaction_end", _release_sqlite_attempt_locks)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _decimal(value: Decimal | int | float) -> Decimal:
    return Decimal(str(value))


def _text(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise QuizEngineError(f"{label} is required")
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def get_bank(db: Session, course_id: UUID, bank_id: UUID) -> QuestionBank:
    bank = (
        db.query(QuestionBank)
        .filter(QuestionBank.id == bank_id, QuestionBank.course_id == course_id)
        .one_or_none()
    )
    if bank is None:
        raise QuizEngineNotFound("Question bank not found")
    return bank


def get_question(db: Session, course_id: UUID, question_id: UUID) -> Question:
    question = (
        db.query(Question)
        .filter(Question.id == question_id, Question.course_id == course_id)
        .one_or_none()
    )
    if question is None:
        raise QuizEngineNotFound("Question not found")
    return question


def get_question_version(
    db: Session, course_id: UUID, version_id: UUID
) -> QuestionVersion:
    version = (
        db.query(QuestionVersion)
        .filter(
            QuestionVersion.id == version_id,
            QuestionVersion.course_id == course_id,
        )
        .one_or_none()
    )
    if version is None:
        raise QuizEngineNotFound("Question version not found")
    return version


def get_quiz(db: Session, course_id: UUID, quiz_id: UUID) -> Quiz:
    quiz = (
        db.query(Quiz)
        .filter(Quiz.id == quiz_id, Quiz.course_id == course_id)
        .one_or_none()
    )
    if quiz is None:
        raise QuizEngineNotFound("Quiz not found")
    return quiz


def get_attempt(db: Session, course_id: UUID, attempt_id: UUID) -> QuizAttempt:
    attempt = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.id == attempt_id,
            QuizAttempt.course_id == course_id,
        )
        .one_or_none()
    )
    if attempt is None:
        raise QuizEngineNotFound("Quiz attempt not found")
    return attempt


def _lock_attempt(db: Session, attempt: QuizAttempt) -> QuizAttempt:
    if db.get_bind().dialect.name == "sqlite":
        held_locks: dict[UUID, RLock] = db.info.setdefault(
            _SESSION_ATTEMPT_LOCKS_KEY, {}
        )
        if attempt.id not in held_locks:
            with _SQLITE_ATTEMPT_LOCKS_GUARD:
                lock = _SQLITE_ATTEMPT_LOCKS.setdefault(attempt.id, RLock())
            lock.acquire()
            held_locks[attempt.id] = lock
    locked = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.id == attempt.id,
            QuizAttempt.course_id == attempt.course_id,
        )
        .populate_existing()
        .with_for_update()
        .one_or_none()
    )
    if locked is None:
        raise QuizEngineNotFound("Quiz attempt not found")
    return locked


def _lock_quiz(db: Session, quiz: Quiz) -> Quiz:
    if db.get_bind().dialect.name == "sqlite":
        held_locks: dict[UUID, RLock] = db.info.setdefault(_SESSION_QUIZ_LOCKS_KEY, {})
        if quiz.id not in held_locks:
            with _SQLITE_QUIZ_LOCKS_GUARD:
                lock = _SQLITE_QUIZ_LOCKS.setdefault(quiz.id, RLock())
            lock.acquire()
            held_locks[quiz.id] = lock
    locked = (
        db.query(Quiz)
        .filter(Quiz.id == quiz.id, Quiz.course_id == quiz.course_id)
        .populate_existing()
        .with_for_update()
        .one_or_none()
    )
    if locked is None:
        raise QuizEngineNotFound("Quiz not found")
    return locked


def list_question_banks(db: Session, course_id: UUID) -> list[QuestionBank]:
    return (
        db.query(QuestionBank)
        .filter(QuestionBank.course_id == course_id)
        .order_by(QuestionBank.name, QuestionBank.created_at)
        .all()
    )


def questions_for_bank(db: Session, bank_id: UUID) -> list[Question]:
    return (
        db.query(Question)
        .filter(Question.bank_id == bank_id)
        .order_by(Question.title, Question.created_at)
        .all()
    )


def versions_for_question(db: Session, question_id: UUID) -> list[QuestionVersion]:
    return (
        db.query(QuestionVersion)
        .filter(QuestionVersion.question_id == question_id)
        .order_by(QuestionVersion.version_number)
        .all()
    )


def create_question_bank(
    db: Session,
    course_id: UUID,
    *,
    name: str,
    description: str | None,
) -> QuestionBank:
    bank = QuestionBank(
        id=uuid4(),
        course_id=course_id,
        name=_text(name, "Question bank name"),
        description=_optional_text(description),
    )
    db.add(bank)
    db.flush()
    return bank


def _objective_options(
    *,
    kind: QuestionKind,
    option_texts: list[str],
    correct_option_index: int,
) -> tuple[list[dict[str, str]], str]:
    texts = (
        ["True", "False"]
        if _enum_value(kind) == QuestionKind.true_false.value
        else [_text(value, "Question option") for value in option_texts]
    )
    if len(texts) < 2 or len(texts) > 10:
        raise QuizEngineError("Objective questions require between 2 and 10 options")
    if len({value.casefold() for value in texts}) != len(texts):
        raise QuizEngineError("Question options must be unique")
    if correct_option_index < 0 or correct_option_index >= len(texts):
        raise QuizEngineError("Correct option index is outside the supplied options")
    options = [{"id": uuid4().hex, "text": value} for value in texts]
    return options, options[correct_option_index]["id"]


def _create_version(
    db: Session,
    question: Question,
    actor: User,
    *,
    kind: QuestionKind,
    prompt: str,
    option_texts: list[str],
    correct_option_index: int,
    default_points: float,
    explanation: str | None,
) -> QuestionVersion:
    current = (
        db.query(func.max(QuestionVersion.version_number))
        .filter(QuestionVersion.question_id == question.id)
        .scalar()
    )
    options, correct_option_id = _objective_options(
        kind=kind,
        option_texts=option_texts,
        correct_option_index=correct_option_index,
    )
    version = QuestionVersion(
        id=uuid4(),
        course_id=question.course_id,
        question_id=question.id,
        version_number=(int(current) + 1) if current is not None else 1,
        kind=kind,
        prompt=_text(prompt, "Question prompt"),
        options=options,
        correct_option_id=correct_option_id,
        default_points=_decimal(default_points),
        explanation=_optional_text(explanation),
        authored_by_user_id=actor.id,
    )
    db.add(version)
    db.flush()
    return version


def create_question(
    db: Session,
    course_id: UUID,
    bank_id: UUID,
    actor: User,
    *,
    title: str,
    kind: QuestionKind,
    prompt: str,
    option_texts: list[str],
    correct_option_index: int,
    default_points: float,
    explanation: str | None,
) -> tuple[Question, QuestionVersion]:
    get_bank(db, course_id, bank_id)
    question = Question(
        id=uuid4(),
        course_id=course_id,
        bank_id=bank_id,
        title=_text(title, "Question title"),
    )
    db.add(question)
    db.flush()
    version = _create_version(
        db,
        question,
        actor,
        kind=kind,
        prompt=prompt,
        option_texts=option_texts,
        correct_option_index=correct_option_index,
        default_points=default_points,
        explanation=explanation,
    )
    return question, version


def create_question_version(
    db: Session,
    course_id: UUID,
    question_id: UUID,
    actor: User,
    **fields: Any,
) -> QuestionVersion:
    question = get_question(db, course_id, question_id)
    return _create_version(db, question, actor, **fields)


def course_item_for_quiz(db: Session, quiz: Quiz) -> CourseItem:
    item = (
        db.query(CourseItem)
        .filter(
            CourseItem.course_id == quiz.course_id,
            CourseItem.kind == "quiz",
            CourseItem.resource_type == "quiz",
            CourseItem.resource_id == quiz.id,
        )
        .one_or_none()
    )
    if item is None:
        raise QuizEngineConflict("Quiz is not linked from course content")
    return item


def quiz_questions(db: Session, quiz_id: UUID) -> list[QuizQuestion]:
    return (
        db.query(QuizQuestion)
        .filter(QuizQuestion.quiz_id == quiz_id)
        .order_by(QuizQuestion.position, QuizQuestion.id)
        .all()
    )


def quiz_max_points(db: Session, quiz_id: UUID) -> Decimal:
    value = (
        db.query(func.sum(QuizQuestion.points))
        .filter(QuizQuestion.quiz_id == quiz_id)
        .scalar()
    )
    return _decimal(value or 0)


def list_quizzes(db: Session, course_id: UUID, *, staff_view: bool) -> list[Quiz]:
    query = db.query(Quiz).filter(Quiz.course_id == course_id)
    if not staff_view:
        query = (
            query.join(
                CourseItem,
                (CourseItem.resource_id == Quiz.id)
                & (CourseItem.course_id == Quiz.course_id),
            )
            .join(CourseSection, CourseSection.id == CourseItem.section_id)
            .filter(
                Quiz.status.in_([QuizStatus.published, QuizStatus.closed]),
                CourseItem.kind == "quiz",
                CourseItem.resource_type == "quiz",
                CourseItem.visibility == CourseContentVisibility.published,
                CourseSection.visibility == CourseContentVisibility.published,
            )
        )
    return query.order_by(Quiz.created_at, Quiz.id).all()


def require_learner_visible_quiz(db: Session, quiz: Quiz) -> None:
    if _enum_value(quiz.status) not in {
        QuizStatus.published.value,
        QuizStatus.closed.value,
    }:
        raise QuizEngineNotFound("Quiz not found")
    item = course_item_for_quiz(db, quiz)
    section = db.get(CourseSection, item.section_id)
    if (
        _enum_value(item.visibility) != CourseContentVisibility.published.value
        or section is None
        or _enum_value(section.visibility) != CourseContentVisibility.published.value
    ):
        raise QuizEngineNotFound("Quiz not found")


def create_quiz(
    db: Session,
    course_id: UUID,
    section_id: UUID,
    actor: User,
    *,
    title: str,
    instructions: str | None,
    attempt_limit: int,
    release_policy: QuizReleasePolicy,
    opens_at: datetime | None,
    closes_at: datetime | None,
) -> Quiz:
    if opens_at and closes_at and _aware(opens_at) >= _aware(closes_at):
        raise QuizEngineError("Quiz close time must be later than its open time")
    quiz = Quiz(
        id=uuid4(),
        course_id=course_id,
        title=_text(title, "Quiz title"),
        instructions=_optional_text(instructions),
        status=QuizStatus.draft,
        release_policy=release_policy,
        attempt_limit=attempt_limit,
        opens_at=opens_at,
        closes_at=closes_at,
        created_by_user_id=actor.id,
    )
    db.add(quiz)
    db.flush()
    CourseContentService(db).create_item(
        course_id,
        section_id,
        title=quiz.title,
        kind="quiz",
        visibility=CourseContentVisibility.draft,
        resource_id=quiz.id,
        payload={},
    )
    return quiz


def add_quiz_question(
    db: Session,
    quiz: Quiz,
    *,
    question_version_id: UUID,
    points: float | None,
) -> QuizQuestion:
    if _enum_value(quiz.status) != QuizStatus.draft.value:
        raise QuizEngineConflict("Published quizzes cannot change question selection")
    if db.query(QuizAttempt.id).filter(QuizAttempt.quiz_id == quiz.id).first():
        raise QuizEngineConflict(
            "A quiz with attempts cannot change question selection"
        )
    version = get_question_version(db, quiz.course_id, question_version_id)
    current = (
        db.query(func.max(QuizQuestion.position))
        .filter(QuizQuestion.quiz_id == quiz.id)
        .scalar()
    )
    link = QuizQuestion(
        id=uuid4(),
        course_id=quiz.course_id,
        quiz_id=quiz.id,
        question_version_id=version.id,
        position=(int(current) + 1) if current is not None else 0,
        points=_decimal(points if points is not None else version.default_points),
    )
    db.add(link)
    db.flush()
    return link


def ensure_quiz_grade_item(db: Session, quiz: Quiz) -> GradeItem:
    total = quiz_max_points(db, quiz.id)
    if total <= 0:
        raise QuizEngineConflict("Quiz must have positive total points")
    category = ensure_default_category(db, quiz.course_id)
    item = (
        db.query(GradeItem)
        .filter(
            GradeItem.course_id == quiz.course_id,
            GradeItem.source_type == QUIZ_GRADE_ITEM_SOURCE_TYPE,
            GradeItem.source_id == quiz.id,
        )
        .one_or_none()
    )
    if item is None:
        current = (
            db.query(func.max(GradeItem.position))
            .filter(GradeItem.course_id == quiz.course_id)
            .scalar()
        )
        item = GradeItem(
            id=uuid4(),
            course_id=quiz.course_id,
            category_id=category.id,
            title=quiz.title,
            description=quiz.instructions,
            position=(int(current) + 1) if current is not None else 0,
            max_points=total,
            calculation_policy={"scoring": "deterministic_objective"},
            release_policy={"quizReleasePolicy": _enum_value(quiz.release_policy)},
            source_type=QUIZ_GRADE_ITEM_SOURCE_TYPE,
            source_id=quiz.id,
        )
        db.add(item)
    else:
        item.title = quiz.title
        item.description = quiz.instructions
        item.max_points = total
        item.release_policy = {"quizReleasePolicy": _enum_value(quiz.release_policy)}
        if item.category_id is None:
            item.category_id = category.id
    db.flush()
    return item


def publish_quiz(db: Session, quiz: Quiz) -> Quiz:
    if _enum_value(quiz.status) == QuizStatus.published.value:
        return quiz
    if _enum_value(quiz.status) != QuizStatus.draft.value:
        raise QuizEngineConflict("Only draft quizzes can be published")
    if not quiz_questions(db, quiz.id):
        raise QuizEngineConflict("Add at least one question before publishing")
    item = course_item_for_quiz(db, quiz)
    ensure_quiz_grade_item(db, quiz)
    now = _now()
    quiz.status = QuizStatus.published
    quiz.published_at = now
    item.visibility = CourseContentVisibility.published
    db.flush()
    return quiz


def close_quiz(db: Session, quiz: Quiz) -> Quiz:
    if _enum_value(quiz.status) == QuizStatus.closed.value:
        return quiz
    if _enum_value(quiz.status) != QuizStatus.published.value:
        raise QuizEngineConflict("Only published quizzes can be closed")
    quiz.status = QuizStatus.closed
    quiz.closed_at = _now()
    db.flush()
    return quiz


def _require_active_student(db: Session, course_id: UUID, user_id: UUID) -> Enrollment:
    enrollment = (
        db.query(Enrollment)
        .filter(
            Enrollment.course_id == course_id,
            Enrollment.user_id == user_id,
            Enrollment.role == CourseMembershipRole.student,
            Enrollment.status == EnrollmentStatus.active,
        )
        .one_or_none()
    )
    if enrollment is None:
        raise QuizEngineConflict("An active student enrollment is required")
    return enrollment


def _require_open_quiz(quiz: Quiz) -> None:
    if _enum_value(quiz.status) != QuizStatus.published.value:
        raise QuizEngineConflict("Quiz is not open for attempts")
    now = _now()
    opens_at = _aware(quiz.opens_at)
    closes_at = _aware(quiz.closes_at)
    if opens_at is not None and now < opens_at:
        raise QuizEngineConflict("Quiz has not opened yet")
    if closes_at is not None and now >= closes_at:
        raise QuizEngineConflict("Quiz attempt window has closed")


def start_attempt(db: Session, quiz: Quiz, user: User) -> QuizAttempt:
    quiz = _lock_quiz(db, quiz)
    require_learner_visible_quiz(db, quiz)
    _require_active_student(db, quiz.course_id, user.id)
    _require_open_quiz(quiz)
    existing = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.quiz_id == quiz.id,
            QuizAttempt.user_id == user.id,
            QuizAttempt.status == QuizAttemptStatus.in_progress,
        )
        .with_for_update()
        .one_or_none()
    )
    if existing is not None:
        return existing
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.quiz_id == quiz.id, QuizAttempt.user_id == user.id)
        .order_by(QuizAttempt.attempt_number)
        .with_for_update()
        .all()
    )
    if len(attempts) >= quiz.attempt_limit:
        raise QuizEngineConflict("Quiz attempt limit reached")
    selected = quiz_questions(db, quiz.id)
    if not selected:
        raise QuizEngineConflict("Quiz has no questions")
    total = sum((_decimal(item.points) for item in selected), Decimal("0"))
    attempt = QuizAttempt(
        id=uuid4(),
        course_id=quiz.course_id,
        quiz_id=quiz.id,
        user_id=user.id,
        attempt_number=len(attempts) + 1,
        status=QuizAttemptStatus.in_progress,
        max_points=total,
    )
    db.add(attempt)
    db.flush()
    for item in selected:
        db.add(
            QuizAttemptQuestion(
                id=uuid4(),
                course_id=quiz.course_id,
                attempt_id=attempt.id,
                question_version_id=item.question_version_id,
                position=item.position,
                points=item.points,
            )
        )
    db.flush()
    return attempt


def attempt_questions(
    db: Session, attempt_id: UUID
) -> list[tuple[QuizAttemptQuestion, QuestionVersion, QuizAnswer | None]]:
    rows = (
        db.query(QuizAttemptQuestion, QuestionVersion)
        .join(
            QuestionVersion,
            QuestionVersion.id == QuizAttemptQuestion.question_version_id,
        )
        .filter(QuizAttemptQuestion.attempt_id == attempt_id)
        .order_by(QuizAttemptQuestion.position, QuizAttemptQuestion.id)
        .all()
    )
    answers = {
        answer.attempt_question_id: answer
        for answer in db.query(QuizAnswer)
        .filter(QuizAnswer.attempt_question_id.in_([item.id for item, _ in rows]))
        .all()
    }
    return [(item, version, answers.get(item.id)) for item, version in rows]


def list_attempts(
    db: Session,
    quiz: Quiz,
    *,
    user_id: UUID | None = None,
) -> list[QuizAttempt]:
    query = db.query(QuizAttempt).filter(QuizAttempt.quiz_id == quiz.id)
    if user_id is not None:
        query = query.filter(QuizAttempt.user_id == user_id)
    return query.order_by(QuizAttempt.user_id, QuizAttempt.attempt_number).all()


def save_answer(
    db: Session,
    quiz: Quiz,
    attempt: QuizAttempt,
    user: User,
    *,
    attempt_question_id: UUID,
    selected_option_id: str,
) -> QuizAnswer:
    quiz = _lock_quiz(db, quiz)
    attempt = _lock_attempt(db, attempt)
    if attempt.quiz_id != quiz.id or attempt.user_id != user.id:
        raise QuizEngineNotFound("Quiz attempt not found")
    _require_active_student(db, quiz.course_id, user.id)
    _require_open_quiz(quiz)
    if _enum_value(attempt.status) != QuizAttemptStatus.in_progress.value:
        raise QuizEngineConflict("Submitted attempts are immutable")
    row = (
        db.query(QuizAttemptQuestion, QuestionVersion)
        .join(
            QuestionVersion,
            QuestionVersion.id == QuizAttemptQuestion.question_version_id,
        )
        .filter(
            QuizAttemptQuestion.id == attempt_question_id,
            QuizAttemptQuestion.attempt_id == attempt.id,
        )
        .one_or_none()
    )
    if row is None:
        raise QuizEngineNotFound("Attempt question not found")
    attempt_question, version = row
    valid_option_ids = {option["id"] for option in version.options}
    if selected_option_id not in valid_option_ids:
        raise QuizEngineError("Selected option does not belong to this question")
    answer = (
        db.query(QuizAnswer)
        .filter(QuizAnswer.attempt_question_id == attempt_question.id)
        .one_or_none()
    )
    if answer is None:
        answer = QuizAnswer(
            id=uuid4(),
            attempt_question_id=attempt_question.id,
            selected_option_id=selected_option_id,
        )
        db.add(answer)
    else:
        answer.selected_option_id = selected_option_id
        answer.is_correct = None
        answer.points_awarded = None
    db.flush()
    return answer


def _project_released_attempt(
    db: Session, quiz: Quiz, attempt: QuizAttempt, actor: User | None
) -> GradeEntry:
    _require_active_student(db, quiz.course_id, attempt.user_id)
    item = ensure_quiz_grade_item(db, quiz)
    entry = (
        db.query(GradeEntry)
        .filter(
            GradeEntry.grade_item_id == item.id,
            GradeEntry.user_id == attempt.user_id,
        )
        .one_or_none()
    )
    if (
        entry is not None
        and entry.source_type == QUIZ_ATTEMPT_ENTRY_SOURCE_TYPE
        and entry.source_id is not None
    ):
        projected_attempt = db.get(QuizAttempt, entry.source_id)
        if (
            projected_attempt is not None
            and projected_attempt.attempt_number > attempt.attempt_number
        ):
            return entry
    if attempt.earned_points is None or attempt.released_at is None:
        raise QuizEngineConflict(
            "Only scored, released attempts can enter the gradebook"
        )
    if entry is None:
        entry = GradeEntry(
            id=uuid4(),
            course_id=quiz.course_id,
            grade_item_id=item.id,
            user_id=attempt.user_id,
            status=GradeEntryStatus.graded,
            points_earned=attempt.earned_points,
            release_state=GradeReleaseState.released,
            released_at=attempt.released_at,
            graded_at=attempt.submitted_at,
            source_type=QUIZ_ATTEMPT_ENTRY_SOURCE_TYPE,
            source_id=attempt.id,
            source_version=f"attempt:{attempt.attempt_number}",
            recorded_by_user_id=actor.id if actor is not None else None,
            note="Deterministically auto-scored objective quiz attempt.",
        )
        db.add(entry)
    else:
        entry.status = GradeEntryStatus.graded
        entry.points_earned = attempt.earned_points
        entry.release_state = GradeReleaseState.released
        entry.released_at = attempt.released_at
        entry.graded_at = attempt.submitted_at
        entry.source_type = QUIZ_ATTEMPT_ENTRY_SOURCE_TYPE
        entry.source_id = attempt.id
        entry.source_version = f"attempt:{attempt.attempt_number}"
        entry.recorded_by_user_id = actor.id if actor is not None else None
        entry.note = "Deterministically auto-scored objective quiz attempt."
    db.flush()
    assert entry.points_earned == attempt.earned_points
    return entry


def release_attempt(
    db: Session,
    quiz: Quiz,
    attempt: QuizAttempt,
    *,
    actor: User | None,
) -> QuizAttempt:
    quiz = _lock_quiz(db, quiz)
    attempt = _lock_attempt(db, attempt)
    if attempt.quiz_id != quiz.id:
        raise QuizEngineNotFound("Quiz attempt not found")
    if _enum_value(attempt.status) == QuizAttemptStatus.in_progress.value:
        raise QuizEngineConflict("Attempt must be submitted before release")
    if _enum_value(attempt.status) != QuizAttemptStatus.released.value:
        attempt.status = QuizAttemptStatus.released
        attempt.released_at = _now()
        db.flush()
    _project_released_attempt(db, quiz, attempt, actor)
    return attempt


def submit_attempt(
    db: Session, quiz: Quiz, attempt: QuizAttempt, user: User
) -> QuizAttempt:
    quiz = _lock_quiz(db, quiz)
    attempt = _lock_attempt(db, attempt)
    if attempt.quiz_id != quiz.id or attempt.user_id != user.id:
        raise QuizEngineNotFound("Quiz attempt not found")
    if _enum_value(attempt.status) in {
        QuizAttemptStatus.submitted.value,
        QuizAttemptStatus.released.value,
    }:
        return attempt
    _require_active_student(db, quiz.course_id, user.id)
    _require_open_quiz(quiz)
    rows = attempt_questions(db, attempt.id)
    total = Decimal("0")
    for attempt_question, version, answer in rows:
        if answer is None:
            continue
        correct = answer.selected_option_id == version.correct_option_id
        answer.is_correct = correct
        answer.points_awarded = attempt_question.points if correct else Decimal("0")
        total += _decimal(answer.points_awarded)
    submitted_at = _now()
    attempt.earned_points = total
    attempt.submitted_at = submitted_at
    attempt.status = QuizAttemptStatus.submitted
    db.flush()
    if _enum_value(quiz.release_policy) == QuizReleasePolicy.immediate.value:
        release_attempt(db, quiz, attempt, actor=None)
    return attempt


__all__ = [
    "QUIZ_ATTEMPT_ENTRY_SOURCE_TYPE",
    "QUIZ_GRADE_ITEM_SOURCE_TYPE",
    "QuizEngineConflict",
    "QuizEngineError",
    "QuizEngineNotFound",
    "add_quiz_question",
    "attempt_questions",
    "close_quiz",
    "course_item_for_quiz",
    "create_question",
    "create_question_bank",
    "create_question_version",
    "create_quiz",
    "ensure_quiz_grade_item",
    "get_attempt",
    "get_bank",
    "get_question",
    "get_question_version",
    "get_quiz",
    "list_attempts",
    "list_question_banks",
    "list_quizzes",
    "publish_quiz",
    "questions_for_bank",
    "quiz_max_points",
    "quiz_questions",
    "release_attempt",
    "require_learner_visible_quiz",
    "save_answer",
    "start_attempt",
    "submit_attempt",
    "versions_for_question",
]
