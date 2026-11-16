import urllib.error

import pytest

from bike_or_bust.gbfs import client


def test_retries_5xx_then_succeeds():
    attempts, sleeps = [], []

    def flaky(url):
        attempts.append(url)
        if len(attempts) < 3:
            raise urllib.error.HTTPError(url, 503, "unavailable", {}, None)
        return b"ok"

    assert client.fetch_with_retry("u", fetch=flaky, sleep=sleeps.append, base_delay=2) == b"ok"
    assert sleeps == [2, 4]


def test_gives_up_after_max_attempts():
    def down(url):
        raise urllib.error.URLError("no route")

    with pytest.raises(client.FetchError, match="after 3 attempts"):
        client.fetch_with_retry("u", fetch=down, attempts=3, sleep=lambda s: None)


def test_4xx_fails_fast_without_retry():
    sleeps = []

    def gone(url):
        raise urllib.error.HTTPError(url, 404, "nf", {}, None)

    with pytest.raises(client.FetchError, match="HTTP 404"):
        client.fetch_with_retry("u", fetch=gone, sleep=sleeps.append)
    assert sleeps == []


def test_city_feed_url():
    city = client.get_city("nyc")
    assert city.feed_url("station_status").endswith("/en/station_status.json")


def test_unknown_city_lists_known_ones():
    with pytest.raises(ValueError, match="known: nyc"):
        client.get_city("atlantis")
