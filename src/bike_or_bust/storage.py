"""Where bytes are kept. The collector depends on this interface, not on a disk or a bucket."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol


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
