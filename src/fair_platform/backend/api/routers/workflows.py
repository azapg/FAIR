from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.plugin import RuntimePlugin
from fair_platform.backend.api.schema.workflow import (
    WorkflowCreate,
    WorkflowRead,
    WorkflowStep,
    WorkflowUpdate,
)
from fair_platform.backend.core.security.dependencies import require_capability
from fair_platform.backend.core.security.permissions import (
    has_capability,
    has_capability_and_owner,
)
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.plugin import Plugin
from fair_platform.backend.data.models.user import User
from fair_platform.backend.data.models.workflow import Workflow

router = APIRouter()


def _runtime_plugin_from_legacy(plugin_obj: Plugin, role: str, settings: dict | None) -> RuntimePlugin:
    return RuntimePlugin(
        plugin_id=plugin_obj.id,
        extension_id=plugin_obj.source,
        name=plugin_obj.name,
        plugin_type="reviewer" if role == "validator" else role,
        action=f"legacy.{plugin_obj.id}",
        description=plugin_obj.description,
        version=plugin_obj.version,
        settings_schema=plugin_obj.settings_schema or {},
        metadata=plugin_obj.meta or {},
        settings=settings or {},
        id=plugin_obj.id,
        type="reviewer" if role == "validator" else role,
        hash=plugin_obj.hash,
        source=plugin_obj.source,
    )


def _steps_from_plugins(plugins: Optional[dict[str, RuntimePlugin]]) -> list[WorkflowStep]:
    if not plugins:
        return []
    ordered_roles = ["transcriber", "grader", "reviewer", "validator"]
    steps: list[WorkflowStep] = []
    order = 0
    for role in ordered_roles:
        plugin = plugins.get(role)
        if plugin is None:
            continue
        plugin_type = "reviewer" if role == "validator" else plugin.plugin_type or role
        normalized = RuntimePlugin.model_validate(
            {
                **plugin.model_dump(mode="python"),
                "plugin_type": plugin_type,
                "type": plugin_type,
            }
        )
        steps.append(
            WorkflowStep(
                id=f"step-{order}-{normalized.plugin_id}",
                order=order,
                plugin_type=plugin_type,
                plugin=normalized,
                settings=normalized.settings,
            )
        )
        order += 1
    return steps


def _normalize_steps(
    payload_steps: list[WorkflowStep] | None,
    payload_plugins: dict[str, RuntimePlugin] | None,
) -> list[WorkflowStep]:
    if payload_steps is not None:
        steps = [WorkflowStep.model_validate(step) for step in payload_steps]
    else:
        steps = _steps_from_plugins(payload_plugins)
    if not steps:
        return []
    steps.sort(key=lambda step: step.order)
    for index, step in enumerate(steps):
        step.order = index
        step.plugin_type = "reviewer" if step.plugin_type == "validator" else step.plugin_type
        step.plugin.plugin_type = step.plugin_type
        step.plugin.type = step.plugin_type
        step.settings = step.settings or step.plugin.settings or {}
        step.plugin.settings = step.settings
    return steps


def _plugins_from_steps(steps: list[WorkflowStep]) -> dict[str, RuntimePlugin]:
    result: dict[str, RuntimePlugin] = {}
    for step in steps:
        result[step.plugin_type] = step.plugin
    return result


def _db_workflow_to_read(wf: Workflow, db: Session) -> WorkflowRead:
    if wf.steps:
        steps = [WorkflowStep.model_validate(step) for step in wf.steps]
    else:
        steps = []
        for role in ("transcriber", "grader", "validator"):
            plugin_hash = getattr(wf, f"{role}_plugin_hash")
            settings = getattr(wf, f"{role}_settings")
            if not plugin_hash:
                continue
            plugin_obj = db.query(Plugin).filter(Plugin.hash == plugin_hash).first()
            if plugin_obj is None:
                continue
            runtime_plugin = _runtime_plugin_from_legacy(plugin_obj, role, settings)
            steps.append(
                WorkflowStep(
                    id=f"legacy-{role}-{plugin_obj.hash}",
                    order=len(steps),
                    plugin_type=runtime_plugin.plugin_type,
                    plugin=runtime_plugin,
                    settings=runtime_plugin.settings,
                )
            )
    steps.sort(key=lambda step: step.order)
    return WorkflowRead(
        id=wf.id,
        course_id=wf.course_id,
        name=wf.name,
        description=wf.description,
        created_by=wf.created_by,
        created_at=wf.created_at,
        updated_at=wf.updated_at,
        archived=wf.archived,
        steps=steps,
        plugins=_plugins_from_steps(steps) or None,
    )


@router.post(
    "/",
    response_model=WorkflowRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_capability("create_workflow"))],
)
def create_workflow(
    payload: WorkflowCreate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if not has_capability(current_user, "create_workflow"):
        raise HTTPException(status_code=403, detail="Not authorized to create workflows")
    course = db.get(Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found")
    if not has_capability_and_owner(current_user, "create_workflow", course.instructor_id):
        raise HTTPException(status_code=403, detail="Only the course instructor or admin can create workflows")

    steps = _normalize_steps(payload.steps, payload.plugins)
    wf = Workflow(
        id=uuid4(),
        course_id=payload.course_id,
        name=payload.name,
        description=payload.description,
        created_by=current_user.id,
        created_at=datetime.now(timezone.utc),
        steps=[step.model_dump(mode="json", by_alias=True) for step in steps],
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return _db_workflow_to_read(wf, db)


@router.get("/", response_model=list[WorkflowRead])
def list_workflows(
    course_id: UUID | None = None,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    if course_id:
        course = db.get(Course, course_id)
        if not course:
            raise HTTPException(status_code=400, detail="Course not found")
        if not has_capability_and_owner(current_user, "read_workflow", course.instructor_id):
            raise HTTPException(status_code=403, detail="Not authorized to list workflows for this course")
    elif not has_capability(current_user, "read_workflow"):
        raise HTTPException(status_code=403, detail="Not authorized to list workflows")

    q = db.query(Workflow)
    if course_id:
        q = q.filter(Workflow.course_id == course_id)
    elif not has_capability(current_user, "update_any_course"):
        q = q.join(Course, Workflow.course_id == Course.id).filter(Course.instructor_id == current_user.id)
    workflows = q.filter(Workflow.archived.is_(False)).all()
    return [_db_workflow_to_read(wf, db) for wf in workflows]


@router.get("/{workflow_id}", response_model=WorkflowRead)
def get_workflow(
    workflow_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    wf = db.get(Workflow, workflow_id)
    if not wf or wf.archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    course = db.get(Course, wf.course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if not has_capability_and_owner(current_user, "read_workflow", course.instructor_id):
        raise HTTPException(status_code=403, detail="Not authorized to get this workflow")
    return _db_workflow_to_read(wf, db)


@router.put("/{workflow_id}", response_model=WorkflowRead)
def update_workflow(
    workflow_id: UUID,
    payload: WorkflowUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    wf = db.get(Workflow, workflow_id)
    if not wf or wf.archived:
        raise HTTPException(status_code=404, detail="Workflow not found")
    course = db.get(Course, wf.course_id)
    if not course:
        raise HTTPException(status_code=400, detail="Cannot find course for this workflow")
    if not has_capability_and_owner(current_user, "update_workflow", course.instructor_id):
        raise HTTPException(status_code=403, detail="Only the course instructor or admin can update this workflow")

    if payload.name is not None:
        wf.name = payload.name
    if payload.description is not None:
        wf.description = payload.description
    if payload.steps is not None or payload.plugins is not None:
        steps = _normalize_steps(payload.steps, payload.plugins)
        wf.steps = [step.model_dump(mode="json", by_alias=True) for step in steps]
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    if wf.archived:
        return None
    course = db.get(Course, wf.course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course not found")
    if not has_capability_and_owner(current_user, "delete_workflow", course.instructor_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the course instructor or admin can delete this workflow")
    wf.archived = True
    wf.updated_at = datetime.now(timezone.utc)
    db.add(wf)
    db.commit()
    return None


__all__ = ["router"]
