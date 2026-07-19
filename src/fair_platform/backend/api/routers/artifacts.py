from __future__ import annotations

import hashlib
import json
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.api.schema.artifact import (
    ArtifactCreate,
    ArtifactUpdate,
    ExecutionArtifactCreate,
    ArtifactLinkCreate,
    ArtifactLinkRead,
    ArtifactPartRead,
    ArtifactRead,
    ArtifactVersionCreate,
    ArtifactVersionRead,
)
from fair_platform.backend.data.database import session_dependency
from fair_platform.backend.data.models import (
    Artifact,
    Execution,
    ExecutionInputArtifact,
    ExecutionEvent,
    User,
)
from fair_platform.backend.data.models.artifact import (
    AccessLevel,
    ArtifactDerivative,
    ArtifactLink,
    ArtifactPart,
    ArtifactStatus,
    ArtifactVersion,
    ArtifactLinkTargetType,
)
from fair_platform.backend.services.artifact_version_service import (
    ArtifactVersionError,
    ArtifactVersionNotFound,
    finalize_artifact_version,
)
from fair_platform.backend.services.artifact_manager import get_artifact_manager
from fair_platform.backend.storage.provider import (
    LocalStorageProvider,
    MultiStorageProvider,
    parse_storage_uri,
)
from fair_platform.backend.data.storage import storage
from fair_platform.backend.core.security.dependencies import (
    get_artifact_download_user,
    require_capability,
)
from fair_platform.backend.core.security.permissions import has_capability
from fair_platform.backend.services.execution_projection import (
    ExecutionProjectionError,
    append_and_project_event,
)
from fair_platform.backend.services.execution_store import (
    EventIdentityConflict,
    ExecutionStoreError,
)
from fair_platform.backend.services.execution_authorization import (
    ExecutionAuthorization,
    require_execution_authorization,
)

router = APIRouter()


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _assert_artifact_access(
    session: Session, artifact: Artifact | None, user: User
) -> Artifact:
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found"
        )
    if not get_artifact_manager(session).can_view(user, artifact):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Artifact access denied"
        )
    return artifact


def _part_read(part: ArtifactPart) -> ArtifactPartRead:
    return ArtifactPartRead(
        id=part.id,
        artifact_version_id=part.artifact_version_id,
        ordinal=part.ordinal,
        name=part.name,
        role=part.role,
        media_type=part.media_type,
        schema_uri=part.schema_uri,
        storage_uri=part.storage_uri,
        inline_json=part.inline_json,
        content_hash=part.content_hash,
        size_bytes=part.size_bytes,
        annotations=part.annotations,
        hash_algorithm=part.hash_algorithm,
        created_at=part.created_at,
    )


def _version_read(version: ArtifactVersion) -> ArtifactVersionRead:
    return ArtifactVersionRead(
        id=version.id,
        artifact_id=version.artifact_id,
        ordinal=version.ordinal,
        state=_enum_value(version.state),
        media_type=version.media_type,
        schema_uri=version.schema_uri,
        metadata=version.metadata_json,
        created_by_user_id=version.created_by_user_id,
        created_by_extension_installation_id=version.created_by_extension_installation_id,
        producing_execution_id=version.producing_execution_id,
        hash_algorithm=version.hash_algorithm,
        content_hash=version.content_hash,
        size_bytes=version.size_bytes,
        provenance=version.provenance,
        supersedes_version_id=version.supersedes_version_id,
        created_at=version.created_at,
        finalized_at=version.finalized_at,
        abandoned_at=version.abandoned_at,
        parts=[_part_read(part) for part in version.parts],
        links=[_link_read(link) for link in version.links if link.retracted_at is None],
    )


def _link_read(link: ArtifactLink) -> ArtifactLinkRead:
    return ArtifactLinkRead(
        id=link.id,
        artifact_version_id=link.artifact_version_id,
        relationship=_enum_value(link.link_relationship),
        target_type=_enum_value(link.target_type),
        target_id=link.target_id,
        metadata=link.metadata_json,
        created_by_execution_id=link.created_by_execution_id,
        created_at=link.created_at,
        retracted_at=link.retracted_at,
    )


def _artifact_read(artifact: Artifact) -> ArtifactRead:
    return ArtifactRead(
        id=artifact.id,
        title=artifact.title,
        artifact_type=artifact.artifact_type,
        mime=artifact.mime,
        meta=artifact.meta,
        status=_enum_value(artifact.status),
        access_level=_enum_value(artifact.access_level),
        course_id=artifact.course_id,
        assignment_id=artifact.assignment_id,
        kind_uri=artifact.kind_uri,
        description=artifact.description,
        owner_user_id=artifact.owner_user_id,
        creator_id=artifact.creator_id,
        sensitivity=artifact.sensitivity,
        access_policy=artifact.access_policy,
        current_version_id=artifact.current_version_id,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
        derivatives=artifact.derivatives,
        versions=[_version_read(version) for version in artifact.versions],
    )


def _load_artifact(session: Session, artifact_id: UUID, user: User) -> Artifact:
    artifact = session.scalar(
        select(Artifact)
        .where(Artifact.id == artifact_id)
        .options(selectinload(Artifact.versions).selectinload(ArtifactVersion.parts))
    )
    return _assert_artifact_access(session, artifact, user)


def _load_execution_input_artifact(
    session: Session,
    *,
    execution_id: UUID,
    artifact_id: UUID,
) -> tuple[ExecutionInputArtifact, Artifact]:
    pinned = session.get(
        ExecutionInputArtifact,
        {"execution_id": execution_id, "artifact_id": artifact_id},
    )
    if pinned is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact is not an input resource for this Execution",
        )
    artifact = session.scalar(
        select(Artifact)
        .where(Artifact.id == artifact_id)
        .options(
            selectinload(Artifact.derivatives),
            selectinload(Artifact.versions).selectinload(ArtifactVersion.parts),
            selectinload(Artifact.versions).selectinload(ArtifactVersion.links),
        )
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return pinned, artifact


@router.post(
    "/artifacts", response_model=ArtifactRead, status_code=status.HTTP_201_CREATED
)
def create_artifact(
    payload: ArtifactCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ArtifactRead:
    artifact = Artifact(
        id=uuid4(),
        title=payload.title,
        artifact_type=payload.kind_uri,
        kind_uri=payload.kind_uri,
        description=payload.description,
        sensitivity=payload.sensitivity,
        access_policy=payload.access_policy,
        creator_id=current_user.id,
        owner_user_id=current_user.id,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return _artifact_read(artifact)


@router.post(
    "/executions/{execution_id}/artifacts",
    response_model=ArtifactRead,
    status_code=status.HTTP_201_CREATED,
)
def create_execution_artifact(
    execution_id: UUID,
    payload: ExecutionArtifactCreate,
    authority: ExecutionAuthorization = Depends(
        require_execution_authorization(("artifacts:write",))
    ),
    db: Session = Depends(session_dependency),
) -> ArtifactRead:
    execution = authority.execution
    installation = authority.installation
    if execution.id != execution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Execution token is not valid for this Execution",
        )
    if execution.cancellation_requested_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Execution cancellation has been requested",
        )
    if execution.initiated_by_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Execution has no user owner for artifact access policy",
        )
    request_id = payload.client_request_id or str(uuid4())
    request_fingerprint = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
    request_content = payload.model_dump(
        by_alias=True,
        mode="json",
        exclude={"client_request_id"},
    )
    request_content_hash = hashlib.sha256(
        json.dumps(request_content, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    producer_event_id = f"artifact-created:{execution.id}:{request_fingerprint}"
    existing_event = db.scalar(
        select(ExecutionEvent).where(
            ExecutionEvent.producer_source == installation.extension_id,
            ExecutionEvent.producer_event_id == producer_event_id,
        )
    )
    if existing_event is not None:
        if existing_event.payload.get("request_content_hash") != request_content_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="clientRequestId was already used for a different artifact request",
            )
        try:
            existing_artifact_id = UUID(str(existing_event.payload["artifact_id"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Existing artifact request has invalid provenance",
            ) from exc
        owner = db.get(User, execution.initiated_by_user_id)
        if owner is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Execution owner no longer exists",
            )
        return _artifact_read(_load_artifact(db, existing_artifact_id, owner))
    if payload.version.supersedes_version_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="execution artifact creation cannot supersede a version from another logical artifact",
        )
    if any(part.storage_uri is not None for part in payload.version.parts):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Execution artifacts cannot reference storageUri directly; "
                "use inlineJson until managed uploads are available"
            ),
        )

    artifact = Artifact(
        id=uuid4(),
        title=payload.title,
        artifact_type=payload.kind_uri,
        kind_uri=payload.kind_uri,
        description=payload.description,
        sensitivity=payload.sensitivity,
        access_policy=payload.access_policy,
        creator_id=execution.initiated_by_user_id,
        owner_user_id=execution.initiated_by_user_id,
    )
    version = ArtifactVersion(
        id=uuid4(),
        artifact_id=artifact.id,
        ordinal=1,
        media_type=payload.version.media_type,
        schema_uri=payload.version.schema_uri,
        metadata_json=payload.version.metadata,
        provenance=payload.version.provenance,
        created_by_extension_installation_id=installation.id,
        producing_execution_id=execution.id,
    )
    version.parts = [
        ArtifactPart(
            id=uuid4(),
            ordinal=index,
            name=part.name,
            role=part.role,
            media_type=part.media_type,
            schema_uri=part.schema_uri,
            storage_uri=part.storage_uri,
            inline_json=part.inline_json,
            content_hash=part.content_hash,
            size_bytes=part.size_bytes,
            annotations=part.annotations,
        )
        for index, part in enumerate(payload.version.parts, start=1)
    ]
    db.add_all([artifact, version])
    try:
        if payload.finalize:
            finalize_artifact_version(db, version.id)
        append_and_project_event(
            db,
            execution_id=execution.id,
            producer_source=installation.extension_id,
            producer_event_id=producer_event_id,
            event_type="artifact.created",
            schema_uri="urn:fair:event:artifact.created:v1",
            payload={
                "artifact_id": str(artifact.id),
                "artifact_version_id": str(version.id),
                "state": _enum_value(version.state),
                "kind_uri": artifact.kind_uri,
                "request_content_hash": request_content_hash,
            },
        )
        db.commit()
    except (
        ArtifactVersionError,
        ArtifactVersionNotFound,
        EventIdentityConflict,
        ExecutionStoreError,
        ExecutionProjectionError,
    ) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    owner = db.get(User, execution.initiated_by_user_id)
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Execution owner no longer exists",
        )
    return _artifact_read(_load_artifact(db, artifact.id, owner))


@router.get(
    "/executions/{execution_id}/artifacts/{artifact_id}",
    response_model=ArtifactRead,
)
def read_execution_input_artifact(
    execution_id: UUID,
    artifact_id: UUID,
    authority: ExecutionAuthorization = Depends(
        require_execution_authorization(("artifacts:read",))
    ),
    db: Session = Depends(session_dependency),
) -> ArtifactRead:
    if authority.execution.id != execution_id:
        raise HTTPException(
            status_code=403, detail="Execution token is not valid for this Execution"
        )
    pinned, artifact = _load_execution_input_artifact(
        db, execution_id=execution_id, artifact_id=artifact_id
    )
    result = _artifact_read(artifact)
    result.versions = [
        version
        for version in result.versions
        if version.id == pinned.artifact_version_id
    ]
    return result


@router.get("/executions/{execution_id}/artifacts/{artifact_id}/download")
def download_execution_input_artifact(
    execution_id: UUID,
    artifact_id: UUID,
    request: Request,
    authority: ExecutionAuthorization = Depends(
        require_execution_authorization(("artifacts:read",))
    ),
    db: Session = Depends(session_dependency),
):
    if authority.execution.id != execution_id:
        raise HTTPException(
            status_code=403, detail="Execution token is not valid for this Execution"
        )
    pinned, artifact = _load_execution_input_artifact(
        db, execution_id=execution_id, artifact_id=artifact_id
    )
    if pinned.artifact_version_id is not None:
        version = next(
            (
                item
                for item in artifact.versions
                if item.id == pinned.artifact_version_id
            ),
            None,
        )
        if version is None:
            raise HTTPException(
                status_code=404, detail="Pinned artifact version not found"
            )
        if len(version.parts) != 1:
            raise HTTPException(
                status_code=409,
                detail="Artifact download requires exactly one pinned content part",
            )
        part = version.parts[0]
        if part.inline_json is not None:
            return JSONResponse(part.inline_json)
        if part.storage_uri is None:
            raise HTTPException(status_code=404, detail="Artifact content not found")
        scheme, key = parse_storage_uri(part.storage_uri)
        manager = get_artifact_manager(db)
        provider = (
            manager.storage_provider.get_provider(scheme)
            if isinstance(manager.storage_provider, MultiStorageProvider)
            else manager.storage_provider
        )
        url = provider.get_presigned_url(key)
        if "application/json" in request.headers.get("accept", ""):
            return JSONResponse({"url": url})
        return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    derivative = artifact.original_derivative
    if derivative is None:
        raise HTTPException(status_code=404, detail="Artifact file not found")
    scheme, key = parse_storage_uri(derivative.storage_uri)
    manager = get_artifact_manager(db)
    provider = (
        manager.storage_provider.get_provider(scheme)
        if isinstance(manager.storage_provider, MultiStorageProvider)
        else manager.storage_provider
    )
    url = provider.get_presigned_url(key)
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"url": url})
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.post(
    "/artifacts/uploads",
    response_model=list[ArtifactRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_capability("create_artifact"))],
)
def upload_artifacts(
    files: list[UploadFile],
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> list[ArtifactRead]:
    """Upload LMS files into the canonical Artifact resource."""
    manager = get_artifact_manager(db)
    try:
        artifacts = manager.create_artifacts_bulk(files, creator=current_user)
        db.commit()
        return [_artifact_read(artifact) for artifact in artifacts]
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


@router.get("/artifacts", response_model=list[ArtifactRead])
def list_artifacts(
    creator_id: UUID | None = Query(None),
    course_id: UUID | None = Query(None),
    assignment_id: UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    access_level: str | None = Query(None),
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> list[ArtifactRead]:
    filters = {
        key: value
        for key, value in {
            "creator_id": creator_id,
            "course_id": course_id,
            "assignment_id": assignment_id,
            "status": status_filter,
            "access_level": access_level,
        }.items()
        if value is not None
    }
    return [
        _artifact_read(artifact)
        for artifact in get_artifact_manager(db).list_artifacts(
            user=current_user, filters=filters
        )
    ]


@router.get("/artifacts/{artifact_id}", response_model=ArtifactRead)
def get_artifact(
    artifact_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ArtifactRead:
    return _artifact_read(_load_artifact(db, artifact_id, current_user))


@router.get("/artifacts/{artifact_id}/download")
def download_artifact(
    artifact_id: UUID,
    request: Request,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_artifact_download_user),
):
    manager = get_artifact_manager(db)
    artifact = manager.get_artifact(artifact_id, current_user)
    derivative = artifact.original_derivative
    if derivative is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Artifact file not found"
        )
    scheme, key = parse_storage_uri(derivative.storage_uri)
    provider = (
        manager.storage_provider.get_provider(scheme)
        if isinstance(manager.storage_provider, MultiStorageProvider)
        else manager.storage_provider
    )
    url = provider.get_presigned_url(key)
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"url": url})
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/artifacts/{artifact_id}/derivatives/{derivative_id}/download")
def download_artifact_derivative(
    artifact_id: UUID,
    derivative_id: UUID,
    request: Request,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    manager = get_artifact_manager(db)
    artifact = manager.get_artifact(artifact_id, current_user)
    derivative = next(
        (item for item in artifact.derivatives if item.id == derivative_id), None
    )
    if derivative is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact derivative not found",
        )
    scheme, key = parse_storage_uri(derivative.storage_uri)
    provider = (
        manager.storage_provider.get_provider(scheme)
        if isinstance(manager.storage_provider, MultiStorageProvider)
        else manager.storage_provider
    )
    url = provider.get_presigned_url(key)
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"url": url})
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.put("/artifacts/{artifact_id}", response_model=ArtifactRead)
def update_artifact(
    artifact_id: UUID,
    payload: ArtifactUpdate,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> ArtifactRead:
    manager = get_artifact_manager(db)
    try:
        artifact = manager.update_artifact(
            artifact_id=artifact_id,
            user=current_user,
            title=payload.title,
            meta=payload.meta,
            access_level=AccessLevel(payload.access_level)
            if payload.access_level
            else None,
            status=ArtifactStatus(payload.status) if payload.status else None,
            course_id=payload.course_id,
            assignment_id=payload.assignment_id,
        )
        db.commit()
        return _artifact_read(artifact)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


@router.delete("/artifacts/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artifact(
    artifact_id: UUID,
    hard_delete: bool = Query(False),
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> None:
    manager = get_artifact_manager(db)
    try:
        manager.delete_artifact(artifact_id, current_user, hard_delete=hard_delete)
        db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


@router.post(
    "/artifacts/{artifact_id}/attachments/assignments/{assignment_id}",
    response_model=ArtifactRead,
)
def attach_artifact_to_assignment(
    artifact_id: UUID,
    assignment_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> ArtifactRead:
    manager = get_artifact_manager(db)
    artifact = manager.attach_to_assignment(artifact_id, assignment_id, current_user)
    db.commit()
    return _artifact_read(artifact)


@router.delete(
    "/artifacts/{artifact_id}/attachments/assignments/{assignment_id}",
    response_model=ArtifactRead,
)
def detach_artifact_from_assignment(
    artifact_id: UUID,
    assignment_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> ArtifactRead:
    manager = get_artifact_manager(db)
    artifact = manager.detach_from_assignment(artifact_id, assignment_id, current_user)
    db.commit()
    return _artifact_read(artifact)


@router.post(
    "/artifacts/{artifact_id}/attachments/submissions/{submission_id}",
    response_model=ArtifactRead,
)
def attach_artifact_to_submission(
    artifact_id: UUID,
    submission_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> ArtifactRead:
    manager = get_artifact_manager(db)
    artifact = manager.attach_to_submission(artifact_id, submission_id, current_user)
    db.commit()
    return _artifact_read(artifact)


@router.delete(
    "/artifacts/{artifact_id}/attachments/submissions/{submission_id}",
    response_model=ArtifactRead,
)
def detach_artifact_from_submission(
    artifact_id: UUID,
    submission_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> ArtifactRead:
    manager = get_artifact_manager(db)
    artifact = manager.detach_from_submission(artifact_id, submission_id, current_user)
    db.commit()
    return _artifact_read(artifact)


@router.post("/artifacts/admin/cleanup-orphaned")
def cleanup_orphaned_artifacts(
    older_than_days: int = Query(7, ge=0),
    hard_delete: bool = Query(False),
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
) -> dict[str, int | bool]:
    if not has_capability(current_user, "cleanup_orphaned_artifacts"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Artifact cleanup capability required",
        )
    manager = get_artifact_manager(db)
    count = manager.cleanup_orphaned(older_than_days, hard_delete)
    db.commit()
    return {
        "cleaned_up": count,
        "hard_delete": hard_delete,
        "older_than_days": older_than_days,
    }


@router.get("/artifact-storage/local/{key:path}")
def download_local_storage_object(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
):
    derivative = db.scalar(
        select(ArtifactDerivative).where(
            ArtifactDerivative.storage_uri == f"local://{key}"
        )
    )
    if derivative is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found"
        )
    get_artifact_manager(db).get_artifact(derivative.artifact_id, current_user)
    provider = LocalStorageProvider(uploads_dir=storage.uploads_dir)
    file_path = provider._safe_path(key)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found"
        )
    return FileResponse(file_path)


@router.post(
    "/artifacts/{artifact_id}/versions",
    response_model=ArtifactVersionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_artifact_version(
    artifact_id: UUID,
    payload: ArtifactVersionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ArtifactVersionRead:
    artifact = _load_artifact(db, artifact_id, current_user)
    last_ordinal = db.scalar(
        select(func.max(ArtifactVersion.ordinal)).where(
            ArtifactVersion.artifact_id == artifact.id
        )
    )
    version = ArtifactVersion(
        id=uuid4(),
        artifact_id=artifact.id,
        ordinal=int(last_ordinal or 0) + 1,
        media_type=payload.media_type,
        schema_uri=payload.schema_uri,
        metadata_json=payload.metadata,
        provenance=payload.provenance,
        supersedes_version_id=payload.supersedes_version_id,
        created_by_user_id=current_user.id,
    )
    version.parts = [
        ArtifactPart(
            id=uuid4(),
            ordinal=index,
            name=part.name,
            role=part.role,
            media_type=part.media_type,
            schema_uri=part.schema_uri,
            storage_uri=part.storage_uri,
            inline_json=part.inline_json,
            content_hash=part.content_hash,
            size_bytes=part.size_bytes,
            annotations=part.annotations,
        )
        for index, part in enumerate(payload.parts, start=1)
    ]
    db.add(version)
    db.commit()
    db.refresh(version)
    return _version_read(version)


@router.get("/artifact-versions/{version_id}", response_model=ArtifactVersionRead)
def get_artifact_version(
    version_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ArtifactVersionRead:
    version = db.scalar(
        select(ArtifactVersion)
        .where(ArtifactVersion.id == version_id)
        .options(
            selectinload(ArtifactVersion.parts), selectinload(ArtifactVersion.artifact)
        )
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="ArtifactVersion not found"
        )
    _assert_artifact_access(db, version.artifact, current_user)
    return _version_read(version)


def _load_version_for_user(
    session: Session, version_id: UUID, user: User
) -> ArtifactVersion:
    version = session.scalar(
        select(ArtifactVersion)
        .where(ArtifactVersion.id == version_id)
        .options(
            selectinload(ArtifactVersion.parts), selectinload(ArtifactVersion.artifact)
        )
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="ArtifactVersion not found"
        )
    _assert_artifact_access(session, version.artifact, user)
    return version


@router.get(
    "/artifact-versions/{version_id}/links",
    response_model=list[ArtifactLinkRead],
)
def list_artifact_links(
    version_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> list[ArtifactLinkRead]:
    version = _load_version_for_user(db, version_id, current_user)
    return [_link_read(link) for link in version.links if link.retracted_at is None]


@router.post(
    "/artifact-versions/{version_id}/links",
    response_model=ArtifactLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def create_artifact_link(
    version_id: UUID,
    payload: ArtifactLinkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ArtifactLinkRead:
    version = _load_version_for_user(db, version_id, current_user)
    if payload.target_type is ArtifactLinkTargetType.artifact_version:
        target_version = db.scalar(
            select(ArtifactVersion)
            .where(ArtifactVersion.id == payload.target_id)
            .options(selectinload(ArtifactVersion.artifact))
        )
        if target_version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Link target not found"
            )
        _assert_artifact_access(db, target_version.artifact, current_user)
    if payload.created_by_execution_id is not None:
        execution = db.get(Execution, payload.created_by_execution_id)
        if execution is None or (
            execution.initiated_by_user_id != current_user.id
            and (
                execution.thread is None
                or execution.thread.owner_user_id != current_user.id
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Execution provenance is not owned by the current user",
            )
    link = ArtifactLink(
        id=uuid4(),
        artifact_version_id=version.id,
        link_relationship=payload.relationship,
        target_type=payload.target_type,
        target_id=payload.target_id,
        metadata_json=payload.metadata,
        created_by_execution_id=payload.created_by_execution_id,
    )
    db.add(link)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Artifact link already exists"
        ) from exc
    db.refresh(link)
    return _link_read(link)


@router.post(
    "/artifact-versions/{version_id}/finalize", response_model=ArtifactVersionRead
)
def finalize_artifact_version_route(
    version_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ArtifactVersionRead:
    version = db.scalar(
        select(ArtifactVersion)
        .where(ArtifactVersion.id == version_id)
        .options(
            selectinload(ArtifactVersion.parts), selectinload(ArtifactVersion.artifact)
        )
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="ArtifactVersion not found"
        )
    _assert_artifact_access(db, version.artifact, current_user)
    try:
        finalized = finalize_artifact_version(db, version.id)
        db.commit()
    except (ArtifactVersionError, ArtifactVersionNotFound) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    db.refresh(finalized)
    return _version_read(finalized)


__all__ = ["router"]
