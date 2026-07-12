from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from fair_platform.backend.data.models.artifact import Artifact
from fair_platform.backend.data.models.artifacts_v2 import (
    ArtifactPart,
    ArtifactVersion,
    ArtifactVersionState,
)


SHA256 = "sha-256"
BUNDLE_MEDIA_TYPE = "application/vnd.fair.artifact.bundle+json"


class ArtifactVersionError(ValueError):
    """Base error for invalid ArtifactVersion operations."""


class ArtifactVersionNotFound(ArtifactVersionError):
    """The requested version does not exist."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return the stable JSON representation used for FAIR content hashes."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hash_part_manifest(parts: list[ArtifactPart]) -> str:
    manifest = [
        {
            "ordinal": part.ordinal,
            "name": part.name,
            "role": part.role,
            "media_type": part.media_type,
            "schema_uri": part.schema_uri,
            "hash_algorithm": part.hash_algorithm,
            "content_hash": part.content_hash,
            "size_bytes": part.size_bytes,
        }
        for part in parts
    ]
    return sha256_hex(canonical_json_bytes(manifest))


def _inline_part_bytes(part: ArtifactPart) -> bytes | None:
    if part.inline_json is None:
        return None
    return canonical_json_bytes(part.inline_json)


def finalize_artifact_version(
    session: Session,
    version_id: UUID,
    *,
    finalized_at: datetime | None = None,
) -> ArtifactVersion:
    """Validate, hash, and finalize one draft ArtifactVersion.

    Inline JSON parts are hashed here. Stored parts must already have a verified
    SHA-256 and byte size from the upload/storage layer; this keeps finalization
    bounded and avoids loading large files into a web worker.
    """

    version = session.scalar(
        select(ArtifactVersion)
        .where(ArtifactVersion.id == version_id)
        .options(selectinload(ArtifactVersion.parts))
    )
    if version is None:
        raise ArtifactVersionNotFound(f"ArtifactVersion {version_id} does not exist")
    state_value = getattr(version.state, "value", version.state)
    if state_value != ArtifactVersionState.draft.value:
        raise ArtifactVersionError(
            f"ArtifactVersion {version_id} is {state_value}; only drafts can finalize"
        )
    if not version.parts:
        raise ArtifactVersionError("an ArtifactVersion must contain at least one part")

    parts = sorted(version.parts, key=lambda part: part.ordinal)
    if [part.ordinal for part in parts] != list(range(1, len(parts) + 1)):
        raise ArtifactVersionError("ArtifactParts must have contiguous ordinals starting at 1")

    total_size = 0
    for part in parts:
        inline_bytes = _inline_part_bytes(part)
        if inline_bytes is not None and part.storage_uri is not None:
            raise ArtifactVersionError(
                f"part {part.name!r} cannot have both inline JSON and storage_uri"
            )
        if inline_bytes is None and part.storage_uri is None:
            raise ArtifactVersionError(
                f"part {part.name!r} must have inline JSON or storage_uri"
            )

        if inline_bytes is not None:
            computed_hash = sha256_hex(inline_bytes)
            computed_size = len(inline_bytes)
            if part.content_hash not in (None, computed_hash):
                raise ArtifactVersionError(f"part {part.name!r} has an incorrect content hash")
            if part.size_bytes not in (None, computed_size):
                raise ArtifactVersionError(f"part {part.name!r} has an incorrect size")
            part.content_hash = computed_hash
            part.size_bytes = computed_size
        elif part.content_hash is None or part.size_bytes is None:
            raise ArtifactVersionError(
                f"stored part {part.name!r} must provide content_hash and size_bytes"
            )

        if part.hash_algorithm not in (None, SHA256):
            raise ArtifactVersionError("Phase 1 supports only sha-256 part hashes")
        part.hash_algorithm = SHA256
        total_size += int(part.size_bytes or 0)

    version.hash_algorithm = SHA256
    version.content_hash = _hash_part_manifest(parts)
    version.size_bytes = total_size
    version.media_type = version.media_type or (
        parts[0].media_type if len(parts) == 1 else BUNDLE_MEDIA_TYPE
    )
    version.provenance = version.provenance or {}
    version.state = ArtifactVersionState.finalized
    version.finalized_at = finalized_at or datetime.now(timezone.utc)

    artifact = session.get(Artifact, version.artifact_id)
    if artifact is not None:
        artifact.current_version_id = version.id
        artifact.updated_at = version.finalized_at

    session.add(version)
    session.flush()
    return version


__all__ = [
    "BUNDLE_MEDIA_TYPE",
    "SHA256",
    "ArtifactVersionError",
    "ArtifactVersionNotFound",
    "canonical_json_bytes",
    "finalize_artifact_version",
    "sha256_hex",
]
