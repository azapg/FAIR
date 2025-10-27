#!/usr/bin/env python3
"""Synchronise project version metadata across packaging files."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
PACKAGE_INIT_PATH = PROJECT_ROOT / "src" / "fair_platform" / "__init__.py"

VERSION_PATTERN = re.compile(r'version\s*=\s*"(?P<version>[^"]+)"')


def normalise_version(raw: str) -> str:
    """Return a cleaned semantic version without a leading ``v`` prefix."""
    version = raw.strip()
    if version.startswith("v"):
        version = version[1:]
    if not version:
        msg = "Version string is empty after normalisation"
        raise ValueError(msg)
    return version


def update_pyproject(version: str) -> None:
    """Replace the ``version`` field inside ``pyproject.toml``."""
    text = PYPROJECT_PATH.read_text(encoding="utf-8")
    new_text, replacements = VERSION_PATTERN.subn(f'version = "{version}"', text, count=1)
    if replacements == 0:
        msg = "Could not locate a version field inside pyproject.toml"
        raise RuntimeError(msg)
    PYPROJECT_PATH.write_text(new_text, encoding="utf-8")


def update_package_init(version: str) -> None:
    """Ensure ``fair_platform.__version__`` matches the provided version."""
    if PACKAGE_INIT_PATH.exists():
        current_text = PACKAGE_INIT_PATH.read_text(encoding="utf-8")
    else:
        current_text = ""

    if "__version__" in current_text:
        pattern = re.compile(r'__version__\s*=\s*"[^"]*"')
        new_text, replacements = pattern.subn(f'__version__ = "{version}"', current_text, count=1)
        if replacements:
            PACKAGE_INIT_PATH.write_text(_ensure_trailing_newline(new_text), encoding="utf-8")
            return

    template = (
        '"""Public package metadata."""\n\n'
        "from __future__ import annotations\n\n"
        "__all__ = [\"__version__\"]\n\n"
        f'__version__ = "{version}"\n'
    )
    PACKAGE_INIT_PATH.write_text(_ensure_trailing_newline(template), encoding="utf-8")


def _ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synchronise version metadata across files")
    parser.add_argument(
        "--version",
        required=True,
        help="Version string to write (leading 'v' prefixes are allowed)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        version = normalise_version(args.version)
    except ValueError as exc:  # pragma: no cover - defensive programming
        print(f"error: {exc}", file=sys.stderr)
        return 2

    update_pyproject(version)
    update_package_init(version)
    print(f"Updated project metadata to version {version}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
