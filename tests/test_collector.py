import gzip
import json
import urllib.error
from datetime import UTC, datetime, timedelta

import pytest

from bike_or_bust import bronze
from bike_or_bust import collector as c
from bike_or_bust.gbfs.client import FetchError, get_city
from bike_or_bust.storage import LocalStorage

PAYLOAD = json.dumps({"last_updated": 1793776516, "ttl": 60, "data": {"stations": []}}).encode()
CITY = get_city("nyc")
NOW = datetime(2026, 11, 4, 7, 22, 41, tzinfo=UTC)


def ok_fetch(url):
    return PAYLOAD


def test_payload_stored_byte_for_byte(tmp_path):
    c.run(CITY, LocalStorage(tmp_path), now=NOW, fetch=ok_fetch)
    key = bronze.raw_key("nyc", "station_status", bronze.floor_to_slot(NOW))
    assert gzip.decompress((tmp_path / key).read_bytes()) == PAYLOAD


def test_metadata_sidecar(tmp_path):
    c.run(CITY, LocalStorage(tmp_path), now=NOW, fetch=ok_fetch)
    key = bronze.meta_key("nyc", "station_status", bronze.floor_to_slot(NOW))
    meta = json.loads((tmp_path / key).read_text())
    assert meta["city"] == "nyc"
    assert meta["source_last_updated"] == 1793776516
    assert meta["fetched_at_utc"] == "2026-11-04T07:22:41+00:00"
    assert meta["payload_bytes"] == len(PAYLOAD)


def test_rerun_same_slot_creates_no_duplicates(tmp_path):
    calls = []

    def counting(url):
        calls.append(url)
        return PAYLOAD

    storage = LocalStorage(tmp_path)
    c.run(CITY, storage, now=NOW, fetch=counting)
    files = sorted(tmp_path.rglob("*"))
    results = c.run(CITY, storage, now=NOW + timedelta(minutes=3), fetch=counting)
    assert sorted(tmp_path.rglob("*")) == files
    assert len(calls) == 2  # second run made no requests
    assert not any(r.written for r in results)


def test_next_slot_writes_new_object(tmp_path):
    storage = LocalStorage(tmp_path)
    c.run(CITY, storage, now=NOW, fetch=ok_fetch)
    c.run(CITY, storage, now=NOW + timedelta(minutes=15), fetch=ok_fetch)
    assert len(list(tmp_path.rglob("station_status_*.json.gz"))) == 2


def test_invalid_json_is_not_persisted(tmp_path):
    with pytest.raises(FetchError):
        c.run(CITY, LocalStorage(tmp_path), now=NOW, fetch=lambda url: b"<html>oops</html>")
    assert list(tmp_path.rglob("*.gz")) == []


def test_one_feed_failing_does_not_block_the_other(tmp_path):
    def half(url):
        if "station_information" in url:
            raise urllib.error.URLError("boom")
        return PAYLOAD

    with pytest.raises(FetchError, match="station_information"):
        c.run(CITY, LocalStorage(tmp_path), now=NOW, fetch=half, sleep=lambda s: None)
    assert len(list(tmp_path.rglob("station_status_*.json.gz"))) == 1
