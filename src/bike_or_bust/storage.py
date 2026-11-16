"""Where bytes are kept. The collector depends on this interface, not on a disk or a bucket."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from botocore.exceptions import ClientError


class Storage(Protocol):
    def exists(self, key: str) -> bool: ...

    def put(self, key: str, data: bytes) -> None: ...


class LocalStorage:
    """Files under a root directory. Writes are atomic: no reader ever sees a partial file."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def exists(self, key: str) -> bool:
        return (self.root / key).exists()

    def put(self, key: str, data: bytes) -> None:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)


class R2Storage:
    """Cloudflare R2 through its S3-compatible API. Objects are private by default."""

    def __init__(self, client: Any, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as e:
            # Only "not found" means absent; auth or network errors must not look like a miss.
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return False
            raise
        return True

    def put(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)


R2_VARS = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")


def storage_from_env(env: Mapping[str, str]) -> Storage:
    """STORAGE_BACKEND=local (default) or r2. r2 never silently falls back to local disk:
    a CI job that lost its secrets must fail, not write to a runner that is thrown away."""
    backend = env.get("STORAGE_BACKEND", "local")
    if backend == "local":
        return LocalStorage(Path(env.get("BRONZE_DIR", "data/bronze")))
    if backend == "r2":
        missing = [v for v in R2_VARS if not env.get(v)]
        if missing:
            raise ValueError(f"STORAGE_BACKEND=r2 but missing: {', '.join(missing)}")
        import boto3  # imported here so local runs and tests do not need credentials

        client = boto3.client(
            "s3",
            endpoint_url=f"https://{env['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            aws_access_key_id=env["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=env["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
        )
        return R2Storage(client, env["R2_BUCKET"])
    raise ValueError(f"unknown STORAGE_BACKEND {backend!r}; use 'local' or 'r2'")
