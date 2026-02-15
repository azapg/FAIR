import pathlib

from fair_platform.backend import storage
from fair_platform.sdk import Artifact


def get_artifact_local_path(artifact: Artifact) -> pathlib.Path:
    """
    Get the local file path of an artifact based on its storage type.

    Args:
        artifact (Artifact): The artifact object.

    Returns:
        pathlib.Path: The local file path of the artifact.

    Raises:
        ValueError: If the storage type is unsupported.
    """
    # Contract for selector-provided artifacts: uploads_dir/{artifact_id}/{title}
    if artifact.id and artifact.title:
        return storage.uploads_dir / artifact.id / artifact.title

    if artifact.storage_type == "local" and artifact.storage_path:
        return storage.uploads_dir / artifact.storage_path

    raise ValueError(
        "Unsupported artifact path contract. Provide either "
        "(id + title) or (storage_type='local' + storage_path)."
    )
