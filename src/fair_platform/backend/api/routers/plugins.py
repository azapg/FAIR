from enum import Enum
from typing import Optional, List

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.data.models import User, UserRole
from fair_platform.sdk import list_plugins, list_grade_plugins, list_validation_plugins, list_transcription_plugins, \
    PluginMeta
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


__all__ = ["router"]
