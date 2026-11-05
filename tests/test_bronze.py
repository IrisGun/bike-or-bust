from datetime import UTC, datetime, timedelta, timezone

import pytest

from bike_or_bust import bronze

NOW = datetime(2026, 11, 4, 7, 22, 41, tzinfo=UTC)


def test_floor_to_slot_floors_to_15_min_utc():
    assert bronze.floor_to_slot(NOW) == datetime(2026, 11, 4, 7, 15, tzinfo=UTC)


def test_floor_to_slot_converts_other_timezones_to_utc():
    ny = timezone(timedelta(hours=-5))
    ts = datetime(2026, 11, 4, 2, 59, 59, tzinfo=ny)
    assert bronze.floor_to_slot(ts) == datetime(2026, 11, 4, 7, 45, tzinfo=UTC)


def test_floor_to_slot_rejects_naive():
    with pytest.raises(ValueError):
        bronze.floor_to_slot(datetime(2026, 11, 4, 7, 0))


def test_keys_are_partitioned_and_paired():
    slot = bronze.floor_to_slot(NOW)
    assert bronze.raw_key("station_status", slot) == (
        "feed=station_status/dt=2026-11-04/hour=07/station_status_20261104T071500Z.json.gz"
    )
    assert bronze.meta_key("station_status", slot).endswith(
        "station_status_20261104T071500Z.meta.json"
    )
