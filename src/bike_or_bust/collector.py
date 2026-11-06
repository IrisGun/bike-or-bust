"""Collect raw GBFS station feeds into the bronze layer.

Payload bytes are stored exactly as received (gzip is storage-level only).
One object per city, feed and 15-minute UTC slot, so re-running a slot never creates duplicates.
Orchestration only: fetching is in gbfs.client, layout in bronze, persistence in storage.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from bike_or_bust import bronze
from bike_or_bust.gbfs.client import (
    City,
    Fetcher,
    FetchError,
    fetch_with_retry,
    get_city,
    http_fetch,
)
from bike_or_bust.storage import Storage, storage_from_env

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Result:
    feed: str
    key: str
    written: bool


def collect_feed(
    city: City,
    feed: str,
    storage: Storage,
    slot: datetime,
    fetched_at: datetime,
    fetch: Fetcher = http_fetch,
    sleep: Callable[[float], None] = time.sleep,
) -> Result:
    key = bronze.raw_key(city.id, feed, slot)
    if storage.exists(key):
        log.info("%s slot %s already collected; skipping", feed, slot.isoformat())
        return Result(feed, key, written=False)

    url = city.feed_url(feed)
    payload = fetch_with_retry(url, fetch=fetch, sleep=sleep)
    try:
        source_last_updated = json.loads(payload).get("last_updated")
    except ValueError as e:
        raise FetchError(f"{url}: response is not valid JSON") from e

    meta = bronze.SnapshotMeta(
        city=city.id,
        feed=feed,
        url=url,
        slot_utc=slot.isoformat(),
        fetched_at_utc=fetched_at.astimezone(UTC).isoformat(),
        source_last_updated=source_last_updated,
        payload_sha256=hashlib.sha256(payload).hexdigest(),
        payload_bytes=len(payload),
    )
    # Metadata first: a payload without metadata would look complete but be unexplained.
    storage.put(bronze.meta_key(city.id, feed, slot), meta.to_json())
    storage.put(key, gzip.compress(payload, mtime=0))
    return Result(feed, key, written=True)


def run(
    city: City,
    storage: Storage,
    now: datetime | None = None,
    fetch: Fetcher = http_fetch,
    sleep: Callable[[float], None] = time.sleep,
) -> list[Result]:
    """Collect every feed of a city for the current slot; raise if any failed (after trying all)."""
    fetched_at = now or datetime.now(UTC)
    slot = bronze.floor_to_slot(fetched_at)
    results, failures = [], []
    for feed in city.feeds:
        try:
            results.append(collect_feed(city, feed, storage, slot, fetched_at, fetch, sleep))
        except FetchError as e:
            log.error("%s", e)
            failures.append(feed)
    if failures:
        raise FetchError(f"feeds failed: {', '.join(failures)}")
    return results


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    storage = storage_from_env(os.environ)
    city = get_city(os.environ.get("CITY", "nyc"))
    for r in run(city, storage):
        log.info("%s -> %s (%s)", r.feed, r.key, "written" if r.written else "skipped")


if __name__ == "__main__":
    main()
