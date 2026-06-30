"""Snapshot object storage abstraction with signed URLs."""
from __future__ import annotations

import logging
import os
import uuid
from typing import Optional, Protocol

logger = logging.getLogger("backend.storage")


class ObjectStore(Protocol):
    def put_snapshot(self, data: bytes, *, content_type: str = "image/jpeg") -> str: ...
    def signed_url(self, ref: str) -> str: ...


class S3ObjectStore:
    def __init__(self, *, endpoint_url, bucket, access_key, secret_key, region, ttl):
        import boto3

        self._bucket = bucket
        self._ttl = ttl
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url or None,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
            region_name=region,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except Exception:
            try:
                self._client.create_bucket(Bucket=self._bucket)
                logger.info("Created bucket %s", self._bucket)
            except Exception as exc:  # pragma: no cover - depends on backend
                logger.warning("Could not ensure bucket %s: %s", self._bucket, exc)

    def put_snapshot(self, data: bytes, *, content_type: str = "image/jpeg") -> str:
        key = f"{uuid.uuid4().hex}.jpg"
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)
        return key

    def signed_url(self, ref: str) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": ref},
            ExpiresIn=self._ttl,
        )


class DiskObjectStore:
    """Development backend: writes files to a local directory.

    Signed URLs are served by the backend's /api/events/{id}/snapshot route in
    dev; here we return a stable relative reference path.
    """

    def __init__(self, base_path: str, *, ttl: int = 300, public_base: str = "/snapshots"):
        self._base = base_path
        self._public_base = public_base
        os.makedirs(base_path, exist_ok=True)

    def put_snapshot(self, data: bytes, *, content_type: str = "image/jpeg") -> str:
        key = f"{uuid.uuid4().hex}.jpg"
        with open(os.path.join(self._base, key), "wb") as fh:
            fh.write(data)
        return key

    def signed_url(self, ref: str) -> str:
        return f"{self._public_base}/{ref}"

    def read(self, ref: str) -> Optional[bytes]:
        path = os.path.join(self._base, ref)
        if not os.path.isfile(path):
            return None
        with open(path, "rb") as fh:
            return fh.read()


def build_object_store(settings) -> ObjectStore:
    if settings.storage_backend == "disk":
        return DiskObjectStore(settings.disk_storage_path, ttl=settings.signed_url_ttl_seconds)
    return S3ObjectStore(
        endpoint_url=settings.s3_endpoint_url,
        bucket=settings.s3_bucket,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        region=settings.s3_region,
        ttl=settings.signed_url_ttl_seconds,
    )
