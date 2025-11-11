from __future__ import annotations

from datetime import UTC, datetime, timedelta

import boto3
from botocore.client import Config

from app.config import settings
from app.schemas import StorageSignRequest, StorageSignResponse


class StorageService:
    def __init__(self) -> None:
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4"),
        )

    def sign(self, payload: StorageSignRequest) -> StorageSignResponse:
        expires = datetime.now(UTC) + timedelta(minutes=5)
        operation = "get_object" if payload.method == "get" else "put_object"
        params = {"Bucket": settings.s3_bucket, "Key": payload.key}
        url = self.client.generate_presigned_url(
            ClientMethod=operation,
            Params=params,
            ExpiresIn=int((expires - datetime.now(UTC)).total_seconds()),
        )
        return StorageSignResponse(url=url, expires_at=expires)
