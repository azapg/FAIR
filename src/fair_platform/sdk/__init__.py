from fair_platform.sdk.schemas import Submission, Submitter, Assignment, Artifact
from fair_platform.sdk.settings import SettingsField, SwitchField, TextField, NumberField
from fair_platform.sdk.plugin import BasePlugin, TranscriptionPlugin, GradePlugin, ValidationPlugin, \
    TranscribedSubmission, GradeResult

__all__ = [
    "Submission",
    "Submitter",
    "Assignment",
    "Artifact",

    "SettingsField",
    "SwitchField",
    "TextField",
    "NumberField",

    "BasePlugin",
    "TranscriptionPlugin",
    "GradePlugin",
    "ValidationPlugin",

    "TranscribedSubmission",
    "GradeResult",
]
