import os
from typing import Literal

DeploymentMode = Literal["COMMUNITY", "ENTERPRISE"]


def get_deployment_mode() -> DeploymentMode:
    raw_mode = (
        os.getenv("FAIR_DEPLOYMENT_MODE")
        or os.getenv("DEPLOYMENT_MODE")
        or "COMMUNITY"
    )
    mode = raw_mode.strip().upper()
    if mode not in {"COMMUNITY", "ENTERPRISE"}:
        return "COMMUNITY"
    return mode  # type: ignore[return-value]

