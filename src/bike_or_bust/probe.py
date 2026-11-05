"""Temporary high-frequency poller for EDA (not part of the production-style pipeline).

Polls station_status every ~60 s (the feed ttl) and stores each distinct source snapshot, keyed by
the source `last_updated`. Used to measure how long stock-outs last and what 15-min sampling misses.
"""

from __future__ import annotations

import gzip
import json
import logging
import os
import sys
import time
from pathlib import Path

from bike_or_bust.gbfs.client import FetchError, feed_url, fetch_with_retry
from bike_or_bust.storage import LocalStorage

log = logging.getLogger(__name__)


def probe_path(root: Path, last_updated: int) -> Path:
    return root / f"station_status_{last_updated}.json.gz"


def poll_once(root: Path, fetch=None) -> bool:
    """Store the current snapshot unless that `last_updated` is already stored. True if written."""
    kwargs = {"fetch": fetch} if fetch else {}
    payload = fetch_with_retry(feed_url("station_status"), **kwargs)
    last_updated = json.loads(payload)["last_updated"]
    path = probe_path(root, last_updated)
    if path.exists():
        return False
    LocalStorage(root).put(path.name, gzip.compress(payload, mtime=0))
    return True


def main(hours: float = 3, interval: float = 60) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    root = Path(os.environ.get("PROBE_DIR", "data/probe"))
    end = time.monotonic() + hours * 3600
    n = 0
    while time.monotonic() < end:
        start = time.monotonic()
        try:
            n += poll_once(root)
        except (FetchError, KeyError, ValueError) as e:
            log.error("poll failed: %s", e)
        time.sleep(max(0, interval - (time.monotonic() - start)))
    log.info("done, %d distinct snapshots stored", n)


if __name__ == "__main__":
    main(*(float(a) for a in sys.argv[1:]))
