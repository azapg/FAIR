from __future__ import annotations

import hashlib
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from fair_platform.backend.api.routers.auth import get_current_user
from fair_platform.backend.core.security.dependencies import require_extension_client
from fair_platform.backend.api.schema.artifact_v2 import (
    ArtifactCreate,
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
    ExecutionEvent,
    ExtensionClient,
    ExtensionInstallation,
    ExtensionInstallationStatus,
    User,
)
from fair_platform.backend.data.models.artifacts_v2 import (
    ArtifactLink,
    ArtifactPart,
    ArtifactVersion,
    ArtifactLinkTargetType,
)
from fair_platform.backend.services.artifact_version_service import (
    ArtifactVersionError,
    ArtifactVersionNotFound,
    finalize_artifact_version,
)
from fair_platform.backend.services.execution_projection import (
    ExecutionProjectionError,
    append_and_project_event,
)
from fair_platform.backend.services.execution_store import (
    EventIdentityConflict,
    ExecutionStoreError,
)
from fair_platform.backend.core.security.permissions import has_capability_or_owner


router = APIRouter()


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _assert_artifact_access(artifact: Artifact | None, user: User) -> Artifact:
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    owner_id = artifact.owner_user_id or artifact.creator_id
    if not has_capability_or_owner(user, "view_all_artifacts", owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Artifact access denied")
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
        kind_uri=artifact.kind_uri,
        description=artifact.description,
        owner_user_id=artifact.owner_user_id,
        creator_id=artifact.creator_id,
        sensitivity=artifact.sensitivity,
        access_policy=artifact.access_policy,
        current_version_id=artifact.current_version_id,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
        versions=[_version_read(version) for version in artifact.versions],
    )


def _load_artifact(session: Session, artifact_id: UUID, user: User) -> Artifact:
    artifact = session.scalar(
        select(Artifact)
        .where(Artifact.id == artifact_id)
        .options(selectinload(Artifact.versions).selectinload(ArtifactVersion.parts))
    )
    return _assert_artifact_access(artifact, user)


@router.post("/artifacts", response_model=ArtifactRead, status_code=status.HTTP_201_CREATED)
def create_v2_artifact(
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
    extension_client: ExtensionClient = Depends(
        require_extension_client(("artifacts:write",))
    ),
    db: Session = Depends(session_dependency),
) -> ArtifactRead:
    execution = db.get(Execution, execution_id)
    if execution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    installation = db.get(ExtensionInstallation, execution.extension_installation_id)
    if (
        installation is None
        or installation.extension_id != extension_client.extension_id
        or _enum_value(installation.status) != ExtensionInstallationStatus.enabled.value
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Extension is not the producing installation for this Execution",
        )
    if execution.initiated_by_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Execution has no user owner for artifact access policy",
        )
    request_id = payload.client_request_id or str(uuid4())
    request_fingerprint = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
    producer_event_id = f"artifact-created:{execution.id}:{request_fingerprint}"
    existing_event = db.scalar(
        select(ExecutionEvent).where(
            ExecutionEvent.producer_source == extension_client.extension_id,
            ExecutionEvent.producer_event_id == producer_event_id,
        )
    )
    if existing_event is not None:
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
            producer_source=extension_client.extension_id,
            producer_event_id=producer_event_id,
            event_type="artifact.created",
            schema_uri="urn:fair:event:artifact.created:v1",
            payload={
                "artifact_id": str(artifact.id),
                "artifact_version_id": str(version.id),
                "state": _enum_value(version.state),
                "kind_uri": artifact.kind_uri,
            },
        )
        db.commit()
    except (ArtifactVersionError, ArtifactVersionNotFound, EventIdentityConflict,
            ExecutionStoreError, ExecutionProjectionError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    owner = db.get(User, execution.initiated_by_user_id)
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Execution owner no longer exists",
        )
    return _artifact_read(_load_artifact(db, artifact.id, owner))


@router.get("/artifacts/{artifact_id}", response_model=ArtifactRead)
def get_v2_artifact(
    artifact_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ArtifactRead:
    return _artifact_read(_load_artifact(db, artifact_id, current_user))


@router.post(
    "/artifacts/{artifact_id}/versions",
    response_model=ArtifactVersionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_v2_artifact_version(
    artifact_id: UUID,
    payload: ArtifactVersionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ArtifactVersionRead:
    artifact = _load_artifact(db, artifact_id, current_user)
    last_ordinal = db.scalar(
        select(func.max(ArtifactVersion.ordinal)).where(ArtifactVersion.artifact_id == artifact.id)
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
def get_v2_artifact_version(
    version_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ArtifactVersionRead:
    version = db.scalar(
        select(ArtifactVersion)
        .where(ArtifactVersion.id == version_id)
        .options(selectinload(ArtifactVersion.parts), selectinload(ArtifactVersion.artifact))
    )
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ArtifactVersion not found")
    _assert_artifact_access(version.artifact, current_user)
    return _version_read(version)


def _load_version_for_user(session: Session, version_id: UUID, user: User) -> ArtifactVersion:
    version = session.scalar(
        select(ArtifactVersion)
        .where(ArtifactVersion.id == version_id)
        .options(selectinload(ArtifactVersion.parts), selectinload(ArtifactVersion.artifact))
    )
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ArtifactVersion not found")
    _assert_artifact_access(version.artifact, user)
    return version


@router.get(
    "/artifact-versions/{version_id}/links",
    response_model=list[ArtifactLinkRead],
)
def list_v2_artifact_links(
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
def create_v2_artifact_link(
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link target not found")
        _assert_artifact_access(target_version.artifact, current_user)
    if payload.created_by_execution_id is not None:
        execution = db.get(Execution, payload.created_by_execution_id)
        if execution is None or (
            execution.initiated_by_user_id != current_user.id
            and (execution.thread is None or execution.thread.owner_user_id != current_user.id)
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
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Artifact link already exists") from exc
    db.refresh(link)
    return _link_read(link)


@router.post("/artifact-versions/{version_id}/finalize", response_model=ArtifactVersionRead)
def finalize_v2_artifact_version(
    version_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(session_dependency),
) -> ArtifactVersionRead:
    version = db.scalar(
        select(ArtifactVersion)
        .where(ArtifactVersion.id == version_id)
        .options(selectinload(ArtifactVersion.parts), selectinload(ArtifactVersion.artifact))
    )
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ArtifactVersion not found")
    _assert_artifact_access(version.artifact, current_user)
    try:
        finalized = finalize_artifact_version(db, version.id)
        db.commit()
    except (ArtifactVersionError, ArtifactVersionNotFound) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    db.refresh(finalized)
    return _version_read(finalized)


__all__ = ["router"]
