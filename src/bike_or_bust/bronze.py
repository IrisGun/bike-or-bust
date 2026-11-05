"""The bronze layout: what is stored, under which key, with what metadata.

Silver reads bronze through this contract, so it lives apart from the code that fetches data.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

SLOT_MINUTES = 15


def floor_to_slot(ts: datetime, minutes: int = SLOT_MINUTES) -> datetime:
    """Floor a timezone-aware datetime to its slot start, in UTC."""
    if ts.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    ts = ts.astimezone(UTC)
    return ts.replace(minute=ts.minute - ts.minute % minutes, second=0, microsecond=0)


def raw_key(feed: str, slot: datetime) -> str:
    stamp = slot.strftime("%Y%m%dT%H%M%SZ")
    return f"feed={feed}/dt={slot:%Y-%m-%d}/hour={slot:%H}/{feed}_{stamp}.json.gz"


def meta_key(feed: str, slot: datetime) -> str:
    return raw_key(feed, slot).removesuffix(".json.gz") + ".meta.json"


@dataclass(frozen=True)
class SnapshotMeta:
    feed: str
    url: str
    slot_utc: str
    fetched_at_utc: str
    source_last_updated: int | None
    payload_sha256: str
    payload_bytes: int

    def to_json(self) -> bytes:
        return json.dumps(asdict(self), indent=2).encode()
