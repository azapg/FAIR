from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.workflow import Workflow
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.data.models.plugin import Plugin  # Needed for plugin name lookup
from fair_platform.backend.api.schema.workflow import (
    WorkflowCreate,
    WorkflowRead,
    WorkflowUpdate,
)
from fair_platform.backend.api.schema.plugin import RuntimePlugin
from fair_platform.backend.api.routers.auth import get_current_user

router = APIRouter()

_WORKFLOW_PLUGIN_ROLES = ("transcriber", "grader", "validator")


def _empty_workflow_plugin_fields() -> Dict[str, Optional[Any]]:
    fields: Dict[str, Optional[Any]] = {}
    for role in _WORKFLOW_PLUGIN_ROLES:
        fields[f"{role}_plugin_id"] = None
        fields[f"{role}_settings"] = None
    return fields


def _extract_workflow_plugin_fields(
    plugins: Optional[Dict[str, RuntimePlugin]],
    *,
    require_at_least_one: bool,
):
    if not plugins:
        if require_at_least_one:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one plugin (transcriber, grader, validator) must be provided.",
            )
        return {}

    unknown_roles = sorted(set(plugins.keys()) - set(_WORKFLOW_PLUGIN_ROLES))
    if unknown_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported workflow plugin roles: {', '.join(unknown_roles)}.",
        )

    matched_roles = 0
    extracted: Dict[str, Optional[Any]] = {}

    for role in _WORKFLOW_PLUGIN_ROLES:
        plugin = plugins.get(role)
        if not plugin:
            continue
        matched_roles += 1
        extracted[f"{role}_plugin_id"] = plugin.id
        extracted[f"{role}_settings"] = plugin.settings

    if require_at_least_one and matched_roles == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one plugin (transcriber, grader, validator) must be provided.",
        )

    return extracted


def _db_workflow_to_read(wf: Workflow, db: Session) -> WorkflowRead:
    plugins: Dict[str, RuntimePlugin] = {}
    for role in _WORKFLOW_PLUGIN_ROLES:
        plugin_id = getattr(wf, f"{role}_plugin_id")
        settings = getattr(wf, f"{role}_settings")
        if plugin_id:
            plugin_obj = db.query(Plugin).filter(Plugin.id == plugin_id).first()
            if not plugin_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Plugin not found for role '{role}' with id {plugin_id}",
                )
            plugins[role] = RuntimePlugin(
                id=plugin_obj.id,
                name=plugin_obj.name,
                type=role,
                settings=settings or {},
                author=plugin_obj.author,
                version=plugin_obj.version,
                author_email=plugin_obj.author_email,
                source=plugin_obj.source,
                settings_schema=plugin_obj.settings_schema,
                hash=plugin_obj.hash,
            )
    return WorkflowRead(
        id=wf.id,
        course_id=wf.course_id,
        name=wf.name,
        description=wf.description,
        created_by=wf.created_by,
        created_at=wf.created_at,
        updated_at=wf.updated_at,
        plugins=plugins if plugins else None,
    )


@router.post("/", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.admin and current_user.role != UserRole.professor:
        raise HTTPException(
            status_code=403, detail="Not authorized to create workflows"
        )

    course = db.get(Course, payload.course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found"
        )

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the course instructor or admin can create workflows",
        )

    plugin_fields = _empty_workflow_plugin_fields()
    plugin_fields.update(
        _extract_workflow_plugin_fields(
            payload.plugins,
            require_at_least_one=False,
        )
    )

    wf = Workflow(
        id=uuid4(),
        course_id=payload.course_id,
        name=payload.name,
        description=payload.description,
        created_by=current_user.id,
        created_at=datetime.now(timezone.utc),
        **plugin_fields,
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return _db_workflow_to_read(wf, db)


@router.get("/", response_model=List[WorkflowRead])
def list_workflows(
    course_id: UUID | None = None,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.admin and current_user.role != UserRole.professor:
        raise HTTPException(status_code=403, detail="Not authorized to list workflows")

    if course_id:
        course = db.get(Course, course_id)
        if not course:
            raise HTTPException(status_code=400, detail="Course not found")
        if (
            current_user.role == UserRole.professor
            and course.instructor_id != current_user.id
        ):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to list workflows for this course",
            )

    q = db.query(Workflow)
    if course_id:
        q = q.filter(Workflow.course_id == course_id)
    workflows = q.all()
    return [_db_workflow_to_read(wf, db) for wf in workflows]


@router.get("/{workflow_id}", response_model=WorkflowRead)
def get_workflow(
    workflow_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.admin and current_user.role != UserRole.professor:
        raise HTTPException(status_code=403, detail="Not authorized to get workflow")

    wf = db.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found"
        )

    course = db.get(Course, wf.course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    if current_user.role == UserRole.professor and course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to get this workflow",
        )
    return _db_workflow_to_read(wf, db)


@router.put("/{workflow_id}", response_model=WorkflowRead)
def update_workflow(
    workflow_id: UUID,
    payload: WorkflowUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.admin and current_user.role != UserRole.professor:
        raise HTTPException(status_code=403, detail="Not authorized to update workflow")

    wf = db.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    course = db.get(Course, wf.course_id)
    if not course:
        raise HTTPException(
            status_code=400,
            detail="Cannot find course for this workflow. Data integrity issue?",
        )

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the course instructor or admin can update this workflow",
        )

    if payload.name is not None:
        wf.name = payload.name
    if payload.description is not None:
        wf.description = payload.description

    plugin_updates = {}
    if payload.plugins is not None:
        plugin_updates = _empty_workflow_plugin_fields()
        plugin_updates.update(
            _extract_workflow_plugin_fields(
                payload.plugins,
                require_at_least_one=True,
            )
        )
        for field, value in plugin_updates.items():
            setattr(wf, field, value)

    if payload.name is not None or payload.description is not None or plugin_updates:
        wf.updated_at = datetime.now(timezone.utc)

    db.add(wf)
    db.commit()
    db.refresh(wf)
    return _db_workflow_to_read(wf, db)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    workflow_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    wf = db.get(Workflow, workflow_id)
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found"
        )

    course = db.get(Course, wf.course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found"
        )

    if current_user.role != UserRole.admin and course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can delete this workflow",
        )

    db.delete(wf)
    db.commit()
    return None


__all__ = ["router"]
