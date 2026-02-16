from uuid import uuid4

from fair_platform.backend.data.models.artifact import Artifact
from fair_platform.backend.data.storage import storage
from tests.conftest import get_auth_token


def create_artifact_with_file(session, creator_id, access_level: str = "public"):
    artifact_id = uuid4()
    filename = "sample.txt"
    storage_path = f"{artifact_id}/{filename}"
    artifact_dir = storage.uploads_dir / str(artifact_id)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    file_path = artifact_dir / filename
    file_path.write_text("example content", encoding="utf-8")

    artifact = Artifact(
        id=artifact_id,
        title="Sample",
        artifact_type="document",
        mime="text/plain",
        storage_path=storage_path,
        storage_type="local",
        creator_id=creator_id,
        status="attached",
        access_level=access_level,
    )
    session.add(artifact)
    session.commit()

    return artifact, file_path


def cleanup_file(file_path):
    try:
        if file_path and file_path.exists():
            file_path.unlink(missing_ok=True)
            parent = file_path.parent
            if parent.exists():
                parent.rmdir()
    except OSError:
        pass


def test_download_allows_authorized_user(test_client, test_db, admin_user):
    file_path = None
    with test_db() as session:
        artifact, file_path = create_artifact_with_file(session, admin_user.id)

    try:
        token = get_auth_token(test_client, admin_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        response = test_client.get(f"/api/artifacts/{artifact.id}/download", headers=headers)

        assert response.status_code == 200
        assert response.content == b"example content"
        assert response.headers["content-type"].startswith("text/plain")
    finally:
        cleanup_file(file_path)


def test_download_enforces_permissions(test_client, test_db, professor_user, student_user):
    file_path = None
    with test_db() as session:
        artifact, file_path = create_artifact_with_file(
            session, professor_user.id, access_level="private"
        )

    try:
        token = get_auth_token(test_client, student_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        response = test_client.get(f"/api/artifacts/{artifact.id}/download", headers=headers)

        assert response.status_code == 403
    finally:
        cleanup_file(file_path)
