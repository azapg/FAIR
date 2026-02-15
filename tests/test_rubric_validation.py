import pytest
from fastapi import HTTPException

from fair_platform.backend.services.rubric_service import validate_rubric_content, WEIGHT_TOLERANCE


class TestRubricValidation:

    def test_valid_rubric_passes(self):
        content = {
            "levels": ["Poor", "Fair", "Good", "Excellent"],
            "criteria": [
                {
                    "name": "Content",
                    "weight": 0.5,
                    "levels": ["Missing", "Incomplete", "Adequate", "Comprehensive"]
                },
                {
                    "name": "Style",
                    "weight": 0.5,
                    "levels": ["Unclear", "Basic", "Clear", "Polished"]
                }
            ]
        }
        validate_rubric_content(content)

    def test_weights_sum_to_one_exact(self):
        content = {
            "levels": ["A", "B"],
            "criteria": [
                {"name": "C1", "weight": 0.25, "levels": ["X", "Y"]},
                {"name": "C2", "weight": 0.25, "levels": ["X", "Y"]},
                {"name": "C3", "weight": 0.5, "levels": ["X", "Y"]},
            ]
        }
        validate_rubric_content(content)

    def test_weights_with_floating_point_edge_case(self):
        content = {
            "levels": ["A", "B"],
            "criteria": [
                {"name": "C1", "weight": 0.1, "levels": ["X", "Y"]},
                {"name": "C2", "weight": 0.2, "levels": ["X", "Y"]},
                {"name": "C3", "weight": 0.3, "levels": ["X", "Y"]},
                {"name": "C4", "weight": 0.4, "levels": ["X", "Y"]},
            ]
        }
        validate_rubric_content(content)

    def test_weights_slightly_over_fails(self):
        content = {
            "levels": ["A", "B"],
            "criteria": [
                {"name": "C1", "weight": 0.5, "levels": ["X", "Y"]},
                {"name": "C2", "weight": 0.51, "levels": ["X", "Y"]},
            ]
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_rubric_content(content)
        assert exc_info.value.status_code == 400
        assert "must sum to 1.0" in exc_info.value.detail

    def test_weights_slightly_under_fails(self):
        content = {
            "levels": ["A", "B"],
            "criteria": [
                {"name": "C1", "weight": 0.5, "levels": ["X", "Y"]},
                {"name": "C2", "weight": 0.49, "levels": ["X", "Y"]},
            ]
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_rubric_content(content)
        assert exc_info.value.status_code == 400
        assert "must sum to 1.0" in exc_info.value.detail

    def test_criterion_levels_count_mismatch_fails(self):
        content = {
            "levels": ["A", "B", "C"],
            "criteria": [
                {"name": "C1", "weight": 1.0, "levels": ["X", "Y"]}
            ]
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_rubric_content(content)
        assert exc_info.value.status_code == 400
        assert "has 2 levels but expected 3" in exc_info.value.detail

    def test_missing_levels_fails(self):
        content = {
            "criteria": [{"name": "C1", "weight": 1.0, "levels": ["X", "Y"]}]
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_rubric_content(content)
        assert exc_info.value.status_code == 400
        assert "levels" in exc_info.value.detail.lower()

    def test_missing_criteria_fails(self):
        content = {
            "levels": ["A", "B"]
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_rubric_content(content)
        assert exc_info.value.status_code == 400
        assert "criteria" in exc_info.value.detail.lower()

    def test_empty_levels_fails(self):
        content = {
            "levels": [],
            "criteria": [{"name": "C1", "weight": 1.0, "levels": []}]
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_rubric_content(content)
        assert exc_info.value.status_code == 400
        assert "at least one level" in exc_info.value.detail.lower()

    def test_empty_criteria_fails(self):
        content = {
            "levels": ["A", "B"],
            "criteria": []
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_rubric_content(content)
        assert exc_info.value.status_code == 400
        assert "at least one criterion" in exc_info.value.detail.lower()

    def test_criterion_missing_weight_fails(self):
        content = {
            "levels": ["A", "B"],
            "criteria": [{"name": "C1", "levels": ["X", "Y"]}]
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_rubric_content(content)
        assert exc_info.value.status_code == 400
        assert "weight" in exc_info.value.detail.lower()

    def test_criterion_missing_name_fails(self):
        content = {
            "levels": ["A", "B"],
            "criteria": [{"weight": 1.0, "levels": ["X", "Y"]}]
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_rubric_content(content)
        assert exc_info.value.status_code == 400
        assert "name" in exc_info.value.detail.lower()

    def test_criterion_missing_levels_fails(self):
        content = {
            "levels": ["A", "B"],
            "criteria": [{"name": "C1", "weight": 1.0}]
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_rubric_content(content)
        assert exc_info.value.status_code == 400
        assert "levels" in exc_info.value.detail.lower()

    def test_non_string_level_fails(self):
        content = {
            "levels": ["A", 123],
            "criteria": [{"name": "C1", "weight": 1.0, "levels": ["X", "Y"]}]
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_rubric_content(content)
        assert exc_info.value.status_code == 400
        assert "string" in exc_info.value.detail.lower()

    def test_non_dict_content_fails(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_rubric_content("not a dict")
        assert exc_info.value.status_code == 400
        assert "dictionary" in exc_info.value.detail.lower()

    def test_integer_weight_works(self):
        content = {
            "levels": ["A", "B"],
            "criteria": [{"name": "C1", "weight": 1, "levels": ["X", "Y"]}]
        }
        validate_rubric_content(content)
