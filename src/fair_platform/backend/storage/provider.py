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
    def __init__(self, uploads_dir: Path | None = None, api_prefix: str = "/api/v1/artifact-storage/local"):
        self.uploads_dir = uploads_dir or storage.uploads_dir
        self.api_prefix = api_prefix.rstrip("/")

    def _safe_path(self, key: str) -> Path:
        candidate = (self.uploads_dir / Path(key)).resolve()
        root = self.uploads_dir.resolve()
        if not candidate.is_relative_to(root):
            raise ValueError("Storage key escapes the uploads directory")
        return candidate

    def put_object(self, key: str, data: BinaryIO, content_type: str) -> str:
        destination = self._safe_path(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        data.seek(0)
        with destination.open("wb") as buffer:
            buffer.write(data.read())
        return f"local://{key}"

    def get_object(self, key: str) -> BinaryIO:
        file_path = self._safe_path(key)
        if not file_path.exists():
            raise FileNotFoundError(key)
        return file_path.open("rb")

    def delete_object(self, key: str) -> None:
        file_path = self._safe_path(key)
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
            from botocore.config import Config
        except ImportError as exc:
            raise RuntimeError("boto3 is required for S3 storage support") from exc

        self.bucket_name = bucket_name
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url or None,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
            config=Config(
                signature_version="s3v4",
                region_name=region_name,
                s3={"addressing_style": "virtual"}
            )
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

class MultiStorageProvider:
    def __init__(self, providers: dict[str, StorageProvider], default_scheme: str):
        if default_scheme not in providers:
            raise HTTPException(
                status_code=500,
                detail=f"Default storage backend '{default_scheme}' is not configured",
            )
        self.providers = providers
        self.default_scheme = default_scheme

    def get_provider(self, scheme: str) -> StorageProvider:
        provider = self.providers.get(scheme)
        if not provider:
            raise HTTPException(
                status_code=500,
                detail=f"Storage backend '{scheme}' is not configured",
            )
        return provider

    def put_object(self, key: str, data: BinaryIO, content_type: str) -> str:
        return self.get_provider(self.default_scheme).put_object(key, data, content_type)

    def get_object(self, key: str) -> BinaryIO:
        return self.get_provider(self.default_scheme).get_object(key)

    def delete_object(self, key: str) -> None:
        self.get_provider(self.default_scheme).delete_object(key)

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return self.get_provider(self.default_scheme).get_presigned_url(key, expires_in)


def get_storage_provider(storage_backend: str | None = None) -> StorageProvider:
    backend = (storage_backend or os.getenv("FAIR_STORAGE_BACKEND", "local")).strip().lower()
    multi_backends = os.getenv("FAIR_STORAGE_BACKENDS")
    if multi_backends:
        schemes = [part.strip().lower() for part in multi_backends.split(",") if part.strip()]
        if not schemes:
            raise HTTPException(status_code=500, detail="FAIR_STORAGE_BACKENDS is empty")
        if backend not in schemes:
            raise HTTPException(
                status_code=500,
                detail="FAIR_STORAGE_BACKEND must be listed in FAIR_STORAGE_BACKENDS",
            )
        providers: dict[str, StorageProvider] = {}
        for scheme in schemes:
            if scheme == "local":
                providers[scheme] = LocalStorageProvider()
            elif scheme == "s3":
                bucket_name = os.getenv("S3_BUCKET_NAME")
                if not bucket_name:
                    raise HTTPException(status_code=500, detail="S3_BUCKET_NAME is not configured")
                providers[scheme] = S3StorageProvider(
                    bucket_name=bucket_name,
                    endpoint_url=os.getenv("S3_ENDPOINT_URL"),
                    access_key=os.getenv("S3_ACCESS_KEY"),
                    secret_key=os.getenv("S3_SECRET_KEY"),
                    region_name=os.getenv("S3_REGION"),
                )
            else:
                raise HTTPException(status_code=500, detail=f"Unsupported storage backend: {scheme}")
        return MultiStorageProvider(providers=providers, default_scheme=backend)
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
    "MultiStorageProvider",
    "S3StorageProvider",
    "StorageProvider",
    "get_storage_provider",
    "parse_storage_uri",
]
