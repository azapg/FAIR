from enum import Enum
from typing import Optional, List, Any

from pydantic import BaseModel, ValidationError

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models import User, UserRole
from fair_platform.sdk import list_plugins, list_grade_plugins, list_validation_plugins, list_transcription_plugins, \
    PluginMeta, get_plugin_object, GradePlugin, TranscribedSubmission, Submission, Submitter, Assignment
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter()


class PluginType(str, Enum):
    transcription = "transcription"
    grade = "grade"
    validation = "validation"
    all = "all"


@router.get("/", response_model=List[PluginMeta])
def list_all_plugins(type_filter: Optional[PluginType] = PluginType.all, user: User = Depends(get_current_user)):
    if user.role != UserRole.admin and user.role != UserRole.professor:
        raise HTTPException(status_code=403, detail="Not authorized to list plugins")

    if type_filter == PluginType.transcription:
        plugins = list_transcription_plugins()
    elif type_filter == PluginType.grade:
        plugins = list_grade_plugins()
    elif type_filter == PluginType.validation:
        plugins = list_validation_plugins()
    else:
        plugins = list_plugins()

    return plugins

class GradeRequest(BaseModel):
    submission_id: str
    plugin_id: str
    plugin_version: Optional[str] = None
    plugin_hash: Optional[str] = None
    settings: dict[str, Any]

# EXAMPLE: plugins/up.allan-zapata.simple-transcriber/transcribe
# with optional payload: version, hash. If not provided, use latest version
# but for that, we need to store multiple versions of the same plugin in storage to actually run them
@router.post("/{plugin_id}/grade")
def grade(plugin_id: str, grade_request: GradeRequest, user: User = Depends(get_current_user)):
    if user.role != UserRole.admin and user.role != UserRole.professor:
        raise HTTPException(status_code=403, detail="Not authorized to grade using plugins")

    plugin = get_plugin_object(plugin_id)

    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    else:
        plugin = plugin()
        
    if not isinstance(plugin, GradePlugin):
        raise HTTPException(status_code=400, detail="Plugin is not a grading plugin")
    try:
        plugin_settings_model = plugin.create_settings_model()
        validated_settings = plugin_settings_model(**grade_request.settings)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    plugin.set_values(validated_settings.model_dump())

    # TODO: just for testing
    submitter = Submitter(id="student123", name="Test Student", email="")
    assignment = Assignment(id="assignment123", title="Test Assignment", description="", deadline="", max_score=100.0)
    original_submission = Submission(id=grade_request.submission_id, submitter=submitter, submitted_at="", assignment=assignment, artifacts=[])
    transcribed_submission = TranscribedSubmission(transcription="This is a test transcription.", confidence=1.0, original_submission=original_submission)
    result = plugin.grade(transcribed_submission)

    return result


__all__ = ["router"]
