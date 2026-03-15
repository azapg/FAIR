from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Protocol
from urllib.parse import quote

from fastapi import HTTPException

from fair_platform.backend.data.storage import storage


class StorageProvider(Protocol):
    def put_object(self, key: str, data: BinaryIO, content_type: str) -> str: ...

    def get_object(self, key: str) -> BinaryIO: ...

    def delete_object(self, key: str) -> None: ...

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str: ...


def parse_storage_uri(storage_uri: str) -> tuple[str, str]:
    if "://" not in storage_uri:
        raise ValueError(f"Invalid storage URI: {storage_uri}")
    scheme, key = storage_uri.split("://", 1)
    return scheme, key.lstrip("/")


class LocalStorageProvider:
    def __init__(self, uploads_dir: Path | None = None, api_prefix: str = "/api/artifacts/storage/local"):
        self.uploads_dir = uploads_dir or storage.uploads_dir
        self.api_prefix = api_prefix.rstrip("/")

    def put_object(self, key: str, data: BinaryIO, content_type: str) -> str:
        destination = self.uploads_dir / Path(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        data.seek(0)
        with destination.open("wb") as buffer:
            buffer.write(data.read())
        return f"local://{key}"

    def get_object(self, key: str) -> BinaryIO:
        file_path = self.uploads_dir / Path(key)
        if not file_path.exists():
            raise FileNotFoundError(key)
        return file_path.open("rb")

    def delete_object(self, key: str) -> None:
        file_path = self.uploads_dir / Path(key)
        if not file_path.exists():
            return
        file_path.unlink()
        parent = file_path.parent
        while parent != self.uploads_dir and parent.exists():
            if any(parent.iterdir()):
                break
            parent.rmdir()
            parent = parent.parent

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        del expires_in
        return f"{self.api_prefix}/{quote(key, safe='/')}"


class S3StorageProvider:
    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region_name: str | None = None,
    ):
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for S3 storage support") from exc

        self.bucket_name = bucket_name
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
        )

    def put_object(self, key: str, data: BinaryIO, content_type: str) -> str:
        data.seek(0)
        self.client.upload_fileobj(
            data,
            self.bucket_name,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return f"s3://{key}"

    def get_object(self, key: str) -> BinaryIO:
        response = self.client.get_object(Bucket=self.bucket_name, Key=key)
        body = response["Body"].read()
        return BytesIO(body)

    def delete_object(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket_name, Key=key)

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )


def get_storage_provider(storage_backend: str | None = None) -> StorageProvider:
    backend = (storage_backend or os.getenv("FAIR_STORAGE_BACKEND", "local")).strip().lower()
    if backend == "local":
        return LocalStorageProvider()
    if backend == "s3":
        bucket_name = os.getenv("S3_BUCKET_NAME")
        if not bucket_name:
            raise HTTPException(status_code=500, detail="S3_BUCKET_NAME is not configured")
        return S3StorageProvider(
            bucket_name=bucket_name,
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            access_key=os.getenv("S3_ACCESS_KEY"),
            secret_key=os.getenv("S3_SECRET_KEY"),
            region_name=os.getenv("S3_REGION"),
        )
    raise HTTPException(status_code=500, detail=f"Unsupported storage backend: {backend}")


__all__ = [
    "LocalStorageProvider",
    "S3StorageProvider",
    "StorageProvider",
    "get_storage_provider",
    "parse_storage_uri",
]
