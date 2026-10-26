"""Release-channel defaults for experimental UI surfaces.

These flags control product visibility, not API authorization. Internal grading,
extension execution, and stored course data remain available in both channels.
"""

import os
from typing import Literal

from fair_platform.backend.core.config import _parse_bool_env

ReleaseChannel = Literal["stable", "nightly"]
EXPERIMENTAL_FEATURES = ("todo", "inbox", "extensions", "course_content", "gradebook")


def get_release_channel() -> ReleaseChannel:
    # Unknown values fail closed, including the retired canary channel.
    return (
        "nightly"
        if os.getenv("FAIR_RELEASE_CHANNEL", "").strip().lower() == "nightly"
        else "stable"
    )


def get_release_features() -> dict[str, bool]:
    nightly = get_release_channel() == "nightly"
    return {
        feature: nightly
        and _parse_bool_env(os.getenv(f"FAIR_FEATURE_{feature.upper()}"), default=True)
        for feature in EXPERIMENTAL_FEATURES
    }
