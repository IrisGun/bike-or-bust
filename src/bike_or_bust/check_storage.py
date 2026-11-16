"""Connectivity check for the configured storage: write a tiny object, read its presence back.

Run with `make storage-check`. Prints no credentials.
"""

from __future__ import annotations

import os

from bike_or_bust.storage import storage_from_env

KEY = "_healthcheck/ping.txt"


def main() -> None:
    storage = storage_from_env(os.environ)
    storage.put(KEY, b"ok")
    assert storage.exists(KEY), "object written but not found"
    print(f"storage ok: {type(storage).__name__} wrote and found {KEY}")


if __name__ == "__main__":
    main()
