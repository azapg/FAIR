"""Executable architecture gates for FAIR's thin platform core.

The platform may persist and authorize educational state, create Executions,
dispatch installed Extension capabilities, and project their accepted outputs.
Provider clients and feature-specific behavior belong to Extensions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fair_platform.backend.main import app


REPO_ROOT = Path(__file__).parents[1]
BACKEND_ROOT = REPO_ROOT / "src/fair_platform/backend"
BUILTIN_EXTENSION = REPO_ROOT / "src/fair_platform/extensions/core/main.py"


def _backend_python() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8") for path in BACKEND_ROOT.rglob("*.py")
    )


def test_backend_has_no_direct_ai_provider_service() -> None:
    source = _backend_python()
    assert not (BACKEND_ROOT / "services/ai_service.py").exists()
    assert "from openai import" not in source
    assert "import openai" not in source
    assert "from zai import" not in source
    assert "FAIR_LLM_API_KEY" not in source


def test_no_feature_specific_ai_route_remains() -> None:
    if "/api/rubrics/generate" in app.openapi()["paths"]:
        pytest.xfail(
            "Rubric generation still bypasses the canonical Execution API. "
            "Remove the feature route after its UI caller uses an installed capability."
        )

def test_platform_does_not_bootstrap_or_start_an_implicit_extension() -> None:
    main_source = (BACKEND_ROOT / "main.py").read_text(encoding="utf-8")
    legacy_markers = {
        "FAIR_ENABLE_CORE_EXTENSION",
        "_ensure_core_extension_client",
        "_start_core_extension",
        "fair_platform.extensions.core.main:app",
    }
    remaining = sorted(marker for marker in legacy_markers if marker in main_source)
    if remaining:
        pytest.xfail(
            "The platform still bootstraps implicit custom behavior: "
            f"{remaining}. Extensions must be installed and operated independently."
        )


def test_no_bundled_core_behavior_extension_remains() -> None:
    if BUILTIN_EXTENSION.exists():
        pytest.xfail(
            "The bundled fair.core behavior package still carries AI, grader, "
            "transcriber, and reviewer logic. Move examples out of the platform package."
        )
