"""
Utility script to export the FastAPI OpenAPI schema to an `openapi.json` file.

Usage:
  python scripts/generate_openapi.py
  python scripts/generate_openapi.py --output openapi.json
  python scripts/generate_openapi.py --output ./frontend-dev/openapi.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from fastapi.openapi.utils import get_openapi


def _resolve_repo_root() -> Path:
    # This file lives at: <repo_root>/scripts/generate_openapi.py
    return Path(__file__).resolve().parents[1]


def _import_app():
    """
    Import the FastAPI app instance from fair_platform.backend.main.

    We prepend the repository root to sys.path so this works when running the
    script directly (without installing the package).
    """
    repo_root = _resolve_repo_root()
    sys.path.insert(0, str(repo_root))

    # Import is intentionally inside the function so sys.path is set first.
    from fair_platform.backend.main import app  # type: ignore

    return app


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate OpenAPI schema JSON from the Fair Platform FastAPI app."
    )
    parser.add_argument(
        "--output",
        "-o",
        default="openapi.json",
        help="Output file path (default: openapi.json in current working directory).",
    )
    args = parser.parse_args()

    app = _import_app()

    # Generate the OpenAPI schema (mirrors FastAPI's default openapi generation),
    # but materializes it so we can save it to disk.
    if not getattr(app, "openapi_schema", None):
        app.openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            routes=app.routes,
        )

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(app.openapi_schema, f, indent=2, ensure_ascii=False)

    print(
        "Successfully generated OpenAPI schema and saved to "
        f"{os.path.abspath(str(output_path))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())