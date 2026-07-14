from io import BytesIO
import os
from uuid import uuid4

import boto3
import pytest

from fair_platform.backend.storage.provider import (
    LocalStorageProvider,
    S3StorageProvider,
    get_storage_provider,
)


def test_local_storage_profile_round_trip_and_path_safety(tmp_path):
    provider = LocalStorageProvider(tmp_path)
    uri = provider.put_object("courses/material.txt", BytesIO(b"hello"), "text/plain")
    assert uri == "local://courses/material.txt"
    assert provider.get_object("courses/material.txt").read() == b"hello"
    assert provider.get_presigned_url("courses/material.txt").endswith("courses/material.txt")
    provider.delete_object("courses/material.txt")
    assert not (tmp_path / "courses" / "material.txt").exists()

    with pytest.raises(ValueError, match="escapes"):
        provider.put_object("../secret.txt", BytesIO(b"no"), "text/plain")


def test_s3_storage_profile_contract(monkeypatch):
    calls: list[tuple] = []

    class Body:
        def read(self):
            return b"from-s3"

    class Client:
        def upload_fileobj(self, data, bucket, key, ExtraArgs):
            calls.append(("put", bucket, key, data.read(), ExtraArgs))

        def get_object(self, *, Bucket, Key):
            calls.append(("get", Bucket, Key))
            return {"Body": Body()}

        def delete_object(self, *, Bucket, Key):
            calls.append(("delete", Bucket, Key))

        def generate_presigned_url(self, operation, *, Params, ExpiresIn):
            calls.append(("url", operation, Params, ExpiresIn))
            return "https://objects.example/signed"

    monkeypatch.setattr(boto3, "client", lambda *_args, **_kwargs: Client())
    provider = S3StorageProvider(bucket_name="fair-institution", region_name="us-east-1")
    assert provider.put_object("a/file.pdf", BytesIO(b"pdf"), "application/pdf") == "s3://a/file.pdf"
    assert provider.get_object("a/file.pdf").read() == b"from-s3"
    assert provider.get_presigned_url("a/file.pdf", 300) == "https://objects.example/signed"
    provider.delete_object("a/file.pdf")
    assert [call[0] for call in calls] == ["put", "get", "url", "delete"]


def test_profile_selection_defaults_local_and_requires_s3_bucket(monkeypatch):
    monkeypatch.delenv("FAIR_STORAGE_BACKEND", raising=False)
    assert isinstance(get_storage_provider(), LocalStorageProvider)

    monkeypatch.setenv("FAIR_STORAGE_BACKEND", "s3")
    monkeypatch.delenv("S3_BUCKET_NAME", raising=False)
    with pytest.raises(Exception, match="S3_BUCKET_NAME"):
        get_storage_provider()


def test_s3_compatible_service_round_trip():
    endpoint = os.getenv("S3_TEST_ENDPOINT", "").strip()
    if not endpoint:
        pytest.skip("S3_TEST_ENDPOINT is not configured")
    access_key = os.getenv("S3_TEST_ACCESS_KEY", "testing")
    secret_key = os.getenv("S3_TEST_SECRET_KEY", "testing")
    region = os.getenv("S3_TEST_REGION", "us-east-1")
    bucket = f"fair-test-{uuid4().hex[:12]}"
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )
    client.create_bucket(Bucket=bucket)
    try:
        provider = S3StorageProvider(
            bucket_name=bucket,
            endpoint_url=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            region_name=region,
        )
        assert provider.put_object("lms/file.txt", BytesIO(b"institution"), "text/plain") == "s3://lms/file.txt"
        assert provider.get_object("lms/file.txt").read() == b"institution"
        assert provider.get_presigned_url("lms/file.txt", 60).startswith(endpoint)
        provider.delete_object("lms/file.txt")
        assert client.list_objects_v2(Bucket=bucket).get("KeyCount") == 0
    finally:
        client.delete_bucket(Bucket=bucket)
