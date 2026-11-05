import gzip
import json

from bike_or_bust import probe


def fetcher(last_updated):
    return lambda url: json.dumps({"last_updated": last_updated, "data": {"stations": []}}).encode()


def test_distinct_snapshots_are_stored_once(tmp_path):
    assert probe.poll_once(tmp_path, fetch=fetcher(100)) is True
    assert probe.poll_once(tmp_path, fetch=fetcher(100)) is False  # same source snapshot
    assert probe.poll_once(tmp_path, fetch=fetcher(160)) is True
    assert len(list(tmp_path.glob("*.json.gz"))) == 2


def test_stored_payload_is_raw(tmp_path):
    probe.poll_once(tmp_path, fetch=fetcher(100))
    stored = gzip.decompress(probe.probe_path(tmp_path, 100).read_bytes())
    assert json.loads(stored)["last_updated"] == 100
