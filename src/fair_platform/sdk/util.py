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
    if artifact.storage_type == "local":
        return storage.uploads_dir / artifact.storage_path
    else:
        raise ValueError(f"Unsupported storage type: {artifact.storage_type}")