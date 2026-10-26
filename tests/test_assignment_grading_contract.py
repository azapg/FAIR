import json
from importlib import import_module
from uuid import uuid4

import pytest
from pydantic import ValidationError

from fair_platform.backend.api.schema.assignment import AssignmentUpdate, PointsGrade
from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.course import Course
from tests.conftest import get_auth_token


points_migration = import_module(
    "fair_platform.backend.alembic.versions.20260727_0028_points_only_grading"
)


def test_points_migration_canonicalizes_only_numeric_scales() -> None:
    assert points_migration._canonical_points({"points": 20}) == {
        "type": "points",
        "value": 20,
    }
    assert points_migration._canonical_points(
        {"type": "percentage", "value": 100}
    ) == {"type": "points", "value": 100}
    assert points_migration._canonical_points(
        {"type": "letter", "value": "A"}
    ) is None
    assert points_migration._canonical_points(
        {"type": "pass_fail", "value": True}
    ) is None


def test_points_grade_accepts_only_positive_point_values() -> None:
    assert PointsGrade.model_validate(
        {"type": "points", "value": 100}
    ).model_dump() == {"type": "points", "value": 100.0}

    for invalid in (
        {"type": "percentage", "value": 100},
        {"type": "letter", "value": "A"},
        {"type": "pass_fail", "value": True},
        {"type": "points", "value": 0},
        {"type": "points", "value": float("inf")},
        {"type": "points", "value": 100, "view": "percentage"},
    ):
        with pytest.raises(ValidationError):
            PointsGrade.model_validate(invalid)


def test_assignment_update_rejects_non_point_grading() -> None:
    with pytest.raises(ValidationError):
        AssignmentUpdate.model_validate(
            {"maxGrade": {"type": "percentage", "value": 100}}
        )


def test_assignment_model_rejects_non_point_grading() -> None:
    with pytest.raises(ValueError, match="exactly"):
        Assignment(
            id=uuid4(),
            course_id=uuid4(),
            title="Invalid scale",
            max_grade={"type": "letter", "value": "A"},
        )


def test_create_assignment_persists_points_contract(
    test_client, test_db, professor_user
) -> None:
    with test_db() as session:
        course = Course(
            id=uuid4(),
            name="Points only",
            instructor_id=professor_user.id,
        )
        session.add(course)
        session.commit()

    headers = {
        "Authorization": f"Bearer {get_auth_token(test_client, professor_user.email)}"
    }
    response = test_client.post(
        "/api/assignments/",
        data={
            "course_id": str(course.id),
            "title": "Point assignment",
            "max_grade": json.dumps({"type": "points", "value": 25}),
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["maxGrade"] == {"type": "points", "value": 25.0}


@pytest.mark.parametrize(
    "max_grade",
    [
        {"type": "percentage", "value": 100},
        {"type": "letter", "value": "A"},
        {"type": "pass_fail", "value": True},
        {"type": "points", "value": -1},
    ],
)
def test_create_assignment_rejects_non_point_grading(
    test_client, test_db, professor_user, max_grade
) -> None:
    with test_db() as session:
        course = Course(
            id=uuid4(),
            name="Points only",
            instructor_id=professor_user.id,
        )
        session.add(course)
        session.commit()

    headers = {
        "Authorization": f"Bearer {get_auth_token(test_client, professor_user.email)}"
    }
    response = test_client.post(
        "/api/assignments/",
        data={
            "course_id": str(course.id),
            "title": "Invalid assignment",
            "max_grade": json.dumps(max_grade),
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Invalid max_grade")
