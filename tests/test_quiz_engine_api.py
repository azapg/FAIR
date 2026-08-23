from __future__ import annotations

from threading import Event, Thread
from uuid import UUID, uuid4

from fair_platform.backend.api.routers.auth import hash_password
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.enrollment import Enrollment, EnrollmentStatus
from fair_platform.backend.data.models.lms_content import (
    CourseContentVisibility,
    CourseSection,
)
from fair_platform.backend.data.models.lms_gradebook import GradeEntry, GradeItem
from fair_platform.backend.data.models.lms_quiz import (
    Quiz,
    QuizAnswer,
    QuizAttempt,
    QuizAttemptQuestion,
)
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.main import app
from fair_platform.backend.services.quiz_engine import release_attempt, start_attempt
from tests.conftest import get_auth_token


def _user(session, name: str, role: UserRole) -> User:
    user = User(
        id=uuid4(),
        name=name,
        email=f"{name.lower()}-{uuid4().hex[:6]}@test.com",
        role=role,
        password_hash=hash_password("test_password_123"),
        is_verified=True,
    )
    session.add(user)
    session.flush()
    return user


def _auth(client, user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {get_auth_token(client, str(user.email))}"}


def _setup(session):
    owner = _user(session, "Owner", UserRole.instructor)
    assistant = _user(session, "Assistant", UserRole.instructor)
    student = _user(session, "Student", UserRole.student)
    outsider = _user(session, "Outsider", UserRole.student)
    removed = _user(session, "Removed", UserRole.student)
    course = Course(id=uuid4(), name="Objective quizzes", instructor_id=owner.id)
    session.add(course)
    session.flush()
    section = CourseSection(
        id=uuid4(),
        course_id=course.id,
        title="Knowledge checks",
        position=0,
        visibility=CourseContentVisibility.published,
    )
    session.add(section)
    session.add_all(
        [
            Enrollment(
                id=uuid4(),
                course_id=course.id,
                user_id=assistant.id,
                role="assistant",
            ),
            Enrollment(
                id=uuid4(),
                course_id=course.id,
                user_id=student.id,
                role="student",
            ),
            Enrollment(
                id=uuid4(),
                course_id=course.id,
                user_id=removed.id,
                role="student",
                status=EnrollmentStatus.removed,
            ),
        ]
    )
    session.commit()
    return owner, assistant, student, outsider, removed, course, section


def _author_question(client, course_id, owner, *, title="Capital"):
    headers = _auth(client, owner)
    bank = client.post(
        f"/api/lms/courses/{course_id}/question-banks",
        json={"name": f"Bank {uuid4().hex[:6]}"},
        headers=headers,
    )
    assert bank.status_code == 201, bank.text
    question = client.post(
        f"/api/lms/courses/{course_id}/question-banks/{bank.json()['id']}/questions",
        json={
            "title": title,
            "kind": "single_choice",
            "prompt": "What is the capital of Panama?",
            "options": ["Panama City", "Colon", "David"],
            "correctOptionIndex": 0,
            "defaultPoints": 4,
            "explanation": "Panama City is the national capital.",
        },
        headers=headers,
    )
    assert question.status_code == 201, question.text
    version = question.json()["versions"][0]
    assert version["correctOptionId"] == version["options"][0]["id"]
    return bank.json(), question.json(), version


def _author_quiz(
    client,
    course_id,
    section_id,
    owner,
    version_id,
    *,
    release_policy="immediate",
    attempt_limit=1,
):
    headers = _auth(client, owner)
    quiz = client.post(
        f"/api/lms/courses/{course_id}/quizzes",
        json={
            "sectionId": str(section_id),
            "title": "Capital check",
            "instructions": "Choose the best answer.",
            "releasePolicy": release_policy,
            "attemptLimit": attempt_limit,
        },
        headers=headers,
    )
    assert quiz.status_code == 201, quiz.text
    assert quiz.json()["status"] == "draft"
    linked = client.post(
        f"/api/lms/courses/{course_id}/quizzes/{quiz.json()['id']}/questions",
        json={"questionVersionId": version_id},
        headers=headers,
    )
    assert linked.status_code == 201, linked.text
    published = client.post(
        f"/api/lms/courses/{course_id}/quizzes/{quiz.json()['id']}/publish",
        headers=headers,
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    assert published.json()["maxPoints"] == 4
    return published.json()


def test_objective_attempt_is_immutable_idempotent_and_projects_released_points(
    test_client, test_db
):
    with test_db() as session:
        owner, _, student, outsider, _, course, section = _setup(session)
    _, question, version = _author_question(test_client, course.id, owner)
    quiz = _author_quiz(
        test_client,
        course.id,
        section.id,
        owner,
        version["id"],
        attempt_limit=2,
    )

    content = test_client.get(
        f"/api/lms/courses/{course.id}/content", headers=_auth(test_client, student)
    )
    assert content.status_code == 200
    assert content.json()["sections"][0]["items"][0]["kind"] == "quiz"
    assert (
        test_client.get(
            f"/api/lms/courses/{course.id}/quizzes",
            headers=_auth(test_client, outsider),
        ).status_code
        == 403
    )

    started = test_client.post(
        f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts",
        headers=_auth(test_client, student),
    )
    assert started.status_code == 201, started.text
    attempt = started.json()
    attempt_question = attempt["questions"][0]
    assert attempt_question["questionVersionId"] == version["id"]
    assert "correctOptionId" not in attempt_question
    assert all("isCorrect" not in option for option in attempt_question["options"])

    # A new bank version never mutates an already selected attempt version.
    next_version = test_client.post(
        f"/api/lms/courses/{course.id}/questions/{question['id']}/versions",
        json={
            "kind": "true_false",
            "prompt": "Panama City is the capital of Panama.",
            "correctOptionIndex": 0,
            "defaultPoints": 2,
        },
        headers=_auth(test_client, owner),
    )
    assert next_version.status_code == 201
    assert len(next_version.json()["versions"]) == 2
    unchanged = test_client.get(
        f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts/{attempt['id']}",
        headers=_auth(test_client, student),
    ).json()
    assert unchanged["questions"][0]["questionVersionId"] == version["id"]

    correct_option_id = version["correctOptionId"]
    answer_url = (
        f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}"
        f"/attempts/{attempt['id']}/answers/{attempt_question['id']}"
    )
    for _ in range(2):
        saved = test_client.put(
            answer_url,
            json={"selectedOptionId": correct_option_id},
            headers=_auth(test_client, student),
        )
        assert saved.status_code == 200, saved.text
    with test_db() as session:
        assert session.query(QuizAnswer).count() == 1
        assert session.query(GradeEntry).count() == 0

    submit_url = (
        f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}"
        f"/attempts/{attempt['id']}/submit"
    )
    submitted = test_client.post(submit_url, headers=_auth(test_client, student))
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "released"
    assert submitted.json()["earnedPoints"] == 4
    repeated = test_client.post(submit_url, headers=_auth(test_client, student))
    assert repeated.status_code == 200
    assert repeated.json()["earnedPoints"] == 4
    late_answer = test_client.put(
        answer_url,
        json={"selectedOptionId": version["options"][1]["id"]},
        headers=_auth(test_client, student),
    )
    assert late_answer.status_code == 409

    with test_db() as session:
        entry = session.query(GradeEntry).one()
        stored_attempt = session.get(QuizAttempt, UUID(attempt["id"]))
        item = session.query(GradeItem).filter(GradeItem.source_type == "quiz").one()
        assert entry.grade_item_id == item.id
        assert entry.source_type == "quiz_attempt"
        assert entry.source_id == stored_attempt.id
        assert entry.points_earned == stored_attempt.earned_points
        assert float(entry.points_earned) == 4

    gradebook = test_client.get(
        f"/api/lms/courses/{course.id}/gradebook",
        headers=_auth(test_client, owner),
    )
    assert gradebook.status_code == 200
    quiz_item = next(
        item for item in gradebook.json()["items"] if item["sourceType"] == "quiz"
    )
    quiz_cell = next(
        cell
        for cell in gradebook.json()["rows"][0]["itemCells"]
        if cell["gradeItemId"] == quiz_item["id"]
    )
    assert quiz_cell["pointsEarned"] == 4

    # A later released attempt becomes the single current quiz projection.
    second = test_client.post(
        f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts",
        headers=_auth(test_client, student),
    ).json()
    wrong_option_id = next(
        option["id"]
        for option in second["questions"][0]["options"]
        if option["id"] != correct_option_id
    )
    test_client.put(
        f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts/{second['id']}/answers/{second['questions'][0]['id']}",
        json={"selectedOptionId": wrong_option_id},
        headers=_auth(test_client, student),
    )
    second_submit = test_client.post(
        f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts/{second['id']}/submit",
        headers=_auth(test_client, student),
    )
    assert second_submit.json()["earnedPoints"] == 0
    # Releasing an older attempt again must not roll the projection backward.
    old_release = test_client.post(
        f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts/{attempt['id']}/release",
        headers=_auth(test_client, owner),
    )
    assert old_release.status_code == 200
    with test_db() as session:
        entry = session.query(GradeEntry).one()
        assert entry.source_id == UUID(second["id"])
        assert float(entry.points_earned) == 0

    locked = test_client.post(
        f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/questions",
        json={"questionVersionId": next_version.json()["versions"][1]["id"]},
        headers=_auth(test_client, owner),
    )
    assert locked.status_code == 409


def test_manual_release_hides_score_and_enforces_membership_and_attempt_limit(
    test_client, test_db
):
    with test_db() as session:
        owner, assistant, student, _, removed, course, section = _setup(session)
    _, _, version = _author_question(test_client, course.id, owner)
    quiz = _author_quiz(
        test_client,
        course.id,
        section.id,
        owner,
        version["id"],
        release_policy="manual",
    )

    assert (
        test_client.post(
            f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts",
            headers=_auth(test_client, removed),
        ).status_code
        == 403
    )
    started = test_client.post(
        f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts",
        headers=_auth(test_client, student),
    ).json()
    question = started["questions"][0]
    saved = test_client.put(
        f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts/{started['id']}/answers/{question['id']}",
        json={"selectedOptionId": version["correctOptionId"]},
        headers=_auth(test_client, student),
    )
    assert saved.status_code == 200
    submitted = test_client.post(
        f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts/{started['id']}/submit",
        headers=_auth(test_client, student),
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "submitted"
    assert submitted.json()["earnedPoints"] is None
    assert submitted.json()["questions"][0]["isCorrect"] is None
    with test_db() as session:
        assert float(session.get(QuizAttempt, UUID(started["id"])).earned_points) == 4
        assert session.query(GradeEntry).count() == 0

    release_url = (
        f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}"
        f"/attempts/{started['id']}/release"
    )
    assert (
        test_client.post(release_url, headers=_auth(test_client, student)).status_code
        == 403
    )
    released = test_client.post(release_url, headers=_auth(test_client, assistant))
    assert released.status_code == 200, released.text
    assert released.json()["earnedPoints"] == 4
    learner_read = test_client.get(
        f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts/{started['id']}",
        headers=_auth(test_client, student),
    )
    assert learner_read.json()["earnedPoints"] == 4
    assert learner_read.json()["questions"][0]["isCorrect"] is True
    assert (
        test_client.post(
            f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts",
            headers=_auth(test_client, student),
        ).status_code
        == 409
    )


def test_publish_scope_and_archived_guards(test_client, test_db):
    with test_db() as session:
        owner, _, student, _, _, course, section = _setup(session)
        other_course = Course(id=uuid4(), name="Other", instructor_id=owner.id)
        other_section = CourseSection(
            id=uuid4(),
            course_id=other_course.id,
            title="Other section",
            position=0,
            visibility=CourseContentVisibility.published,
        )
        session.add_all([other_course, other_section])
        session.commit()
    _, _, version = _author_question(test_client, course.id, owner)
    other_quiz = test_client.post(
        f"/api/lms/courses/{other_course.id}/quizzes",
        json={"sectionId": str(other_section.id), "title": "Other quiz"},
        headers=_auth(test_client, owner),
    )
    assert other_quiz.status_code == 201
    cross_course = test_client.post(
        f"/api/lms/courses/{other_course.id}/quizzes/{other_quiz.json()['id']}/questions",
        json={"questionVersionId": version["id"]},
        headers=_auth(test_client, owner),
    )
    assert cross_course.status_code == 404
    empty_publish = test_client.post(
        f"/api/lms/courses/{other_course.id}/quizzes/{other_quiz.json()['id']}/publish",
        headers=_auth(test_client, owner),
    )
    assert empty_publish.status_code == 409

    draft_quiz = test_client.post(
        f"/api/lms/courses/{course.id}/quizzes",
        json={"sectionId": str(section.id), "title": "Draft quiz"},
        headers=_auth(test_client, owner),
    )
    assert draft_quiz.status_code == 201
    learner_list = test_client.get(
        f"/api/lms/courses/{course.id}/quizzes",
        headers=_auth(test_client, student),
    )
    assert learner_list.json() == []
    assert (
        test_client.get(
            f"/api/lms/courses/{course.id}/quizzes/{draft_quiz.json()['id']}",
            headers=_auth(test_client, student),
        ).status_code
        == 404
    )
    deleted_draft = test_client.delete(
        f"/api/lms/courses/{course.id}/items/{draft_quiz.json()['courseItemId']}",
        headers=_auth(test_client, owner),
    )
    assert deleted_draft.status_code == 204
    assert (
        test_client.get(
            f"/api/lms/courses/{course.id}/quizzes/{draft_quiz.json()['id']}",
            headers=_auth(test_client, owner),
        ).status_code
        == 404
    )

    _, _, local_version = _author_question(
        test_client, course.id, owner, title="Close guard"
    )
    closed_quiz = _author_quiz(
        test_client,
        course.id,
        section.id,
        owner,
        local_version["id"],
    )
    closed = test_client.post(
        f"/api/lms/courses/{course.id}/quizzes/{closed_quiz['id']}/close",
        headers=_auth(test_client, owner),
    )
    assert closed.status_code == 200
    assert (
        test_client.post(
            f"/api/lms/courses/{course.id}/quizzes/{closed_quiz['id']}/attempts",
            headers=_auth(test_client, student),
        ).status_code
        == 409
    )
    assert (
        test_client.delete(
            f"/api/lms/courses/{course.id}/items/{closed_quiz['courseItemId']}",
            headers=_auth(test_client, owner),
        ).status_code
        == 409
    )
    assert (
        test_client.delete(
            f"/api/lms/courses/{course.id}/sections/{section.id}",
            headers=_auth(test_client, owner),
        ).status_code
        == 409
    )
    assert (
        test_client.get(
            f"/api/lms/courses/{course.id}/quizzes/{closed_quiz['id']}",
            headers=_auth(test_client, owner),
        ).status_code
        == 200
    )

    draft_section = test_client.post(
        f"/api/lms/courses/{course.id}/sections",
        json={"title": "Disposable drafts"},
        headers=_auth(test_client, owner),
    ).json()
    disposable_quiz = test_client.post(
        f"/api/lms/courses/{course.id}/quizzes",
        json={"sectionId": draft_section["id"], "title": "Disposable quiz"},
        headers=_auth(test_client, owner),
    ).json()
    assert (
        test_client.delete(
            f"/api/lms/courses/{course.id}/sections/{draft_section['id']}",
            headers=_auth(test_client, owner),
        ).status_code
        == 204
    )
    assert (
        test_client.get(
            f"/api/lms/courses/{course.id}/quizzes/{disposable_quiz['id']}",
            headers=_auth(test_client, owner),
        ).status_code
        == 404
    )

    with test_db() as session:
        session.get(Course, course.id).is_archived = True
        session.commit()
    assert (
        test_client.get(
            f"/api/lms/courses/{course.id}/quizzes",
            headers=_auth(test_client, owner),
        ).status_code
        == 200
    )
    archived_write = test_client.post(
        f"/api/lms/courses/{course.id}/question-banks",
        json={"name": "Blocked"},
        headers=_auth(test_client, owner),
    )
    assert archived_write.status_code == 409


def test_archived_course_blocks_in_progress_answer_writes(test_client, test_db):
    with test_db() as session:
        owner, _, student, _, _, course, section = _setup(session)
    _, _, version = _author_question(test_client, course.id, owner)
    quiz = _author_quiz(test_client, course.id, section.id, owner, version["id"])
    started = test_client.post(
        f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts",
        headers=_auth(test_client, student),
    ).json()
    with test_db() as session:
        session.get(Course, course.id).is_archived = True
        session.commit()
    answer = test_client.put(
        f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts/{started['id']}/answers/{started['questions'][0]['id']}",
        json={"selectedOptionId": version["correctOptionId"]},
        headers=_auth(test_client, student),
    )
    assert answer.status_code == 409
    assert (
        test_client.get(
            f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts/{started['id']}",
            headers=_auth(test_client, student),
        ).status_code
        == 200
    )
    with test_db() as session:
        assert session.query(QuizAttemptQuestion).count() == 1
        assert session.query(QuizAnswer).count() == 0


def test_sqlite_first_attempt_start_is_idempotent_across_sessions(test_client, test_db):
    with test_db() as session:
        owner, _, student, _, _, course, section = _setup(session)
    _, _, version = _author_question(test_client, course.id, owner)
    quiz = _author_quiz(
        test_client,
        course.id,
        section.id,
        owner,
        version["id"],
        attempt_limit=2,
    )

    first_ready = Event()
    allow_first_commit = Event()
    results: list[UUID] = []
    errors: list[Exception] = []

    def start(wait_before_commit: bool) -> None:
        try:
            with test_db() as session:
                attempt = start_attempt(
                    session,
                    session.get(Quiz, UUID(quiz["id"])),
                    session.get(User, student.id),
                )
                if wait_before_commit:
                    first_ready.set()
                    assert allow_first_commit.wait(5)
                session.commit()
                results.append(attempt.id)
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    first = Thread(target=start, args=(True,))
    second = Thread(target=start, args=(False,))
    first.start()
    assert first_ready.wait(5)
    second.start()
    allow_first_commit.set()
    first.join(5)
    second.join(5)

    assert not first.is_alive() and not second.is_alive()
    assert errors == []
    assert len(results) == 2
    assert results[0] == results[1]
    with test_db() as session:
        assert (
            session.query(QuizAttempt).filter_by(quiz_id=UUID(quiz["id"])).count() == 1
        )


def test_sqlite_concurrent_releases_keep_the_latest_attempt_projection(
    test_client, test_db
):
    with test_db() as session:
        owner, _, student, _, _, course, section = _setup(session)
    _, _, version = _author_question(test_client, course.id, owner)
    quiz = _author_quiz(
        test_client,
        course.id,
        section.id,
        owner,
        version["id"],
        release_policy="manual",
        attempt_limit=2,
    )
    attempts = []
    for selected_option_id in (
        version["correctOptionId"],
        version["options"][1]["id"],
    ):
        started = test_client.post(
            f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts",
            headers=_auth(test_client, student),
        ).json()
        test_client.put(
            f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts/{started['id']}/answers/{started['questions'][0]['id']}",
            json={"selectedOptionId": selected_option_id},
            headers=_auth(test_client, student),
        )
        submitted = test_client.post(
            f"/api/lms/courses/{course.id}/quizzes/{quiz['id']}/attempts/{started['id']}/submit",
            headers=_auth(test_client, student),
        )
        assert submitted.status_code == 200
        attempts.append(UUID(started["id"]))

    first_ready = Event()
    allow_first_commit = Event()
    errors: list[Exception] = []

    def release(attempt_id: UUID, wait_before_commit: bool) -> None:
        try:
            with test_db() as session:
                release_attempt(
                    session,
                    session.get(Quiz, UUID(quiz["id"])),
                    session.get(QuizAttempt, attempt_id),
                    actor=session.get(User, owner.id),
                )
                if wait_before_commit:
                    first_ready.set()
                    assert allow_first_commit.wait(5)
                session.commit()
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    older = Thread(target=release, args=(attempts[0], True))
    newer = Thread(target=release, args=(attempts[1], False))
    older.start()
    assert first_ready.wait(5)
    newer.start()
    allow_first_commit.set()
    older.join(5)
    newer.join(5)

    assert not older.is_alive() and not newer.is_alive()
    assert errors == []
    with test_db() as session:
        entry = session.query(GradeEntry).one()
        assert entry.source_id == attempts[1]
        assert float(entry.points_earned) == 0


def test_quiz_openapi_documents_routes_without_student_answer_keys():
    schema = app.openapi()
    assert "/api/lms/courses/{course_id}/quizzes/{quiz_id}/attempts" in schema["paths"]
    assert (
        "/api/lms/courses/{course_id}/quizzes/{quiz_id}/attempts/{attempt_id}/submit"
        in schema["paths"]
    )
    attempt_question = schema["components"]["schemas"]["AttemptQuestionRead"]
    assert "correctOptionId" not in attempt_question["properties"]
    authoring_version = schema["components"]["schemas"]["QuestionVersionAuthoringRead"]
    assert "correctOptionId" in authoring_version["properties"]
