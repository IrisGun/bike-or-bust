"""HTTP access to the GBFS feeds: fetching with retry. Knows nothing about storage."""

from __future__ import annotations

import logging
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

log = logging.getLogger(__name__)

Fetcher = Callable[[str], bytes]


class FetchError(Exception):
    """The source could not be read or returned unusable data (not a bug in our code)."""


@dataclass(frozen=True)
class City:
    """A GBFS bike-share system. Adding a city means adding one entry to CITIES."""

    id: str
    name: str
    timezone: str
    base_url: str
    feeds: tuple[str, ...] = ("station_status", "station_information")

    def feed_url(self, feed: str) -> str:
        return f"{self.base_url}/{feed}.json"


# Take NYC as the pioneer for now
CITIES: dict[str, City] = {
    "nyc": City(
        id="nyc",
        name="New York City",
        timezone="America/New_York",
        base_url="https://gbfs.lyft.com/gbfs/1.1/bkn/en",
    ),
}


def get_city(city_id: str) -> City:
    try:
        return CITIES[city_id]
    except KeyError:
        raise ValueError(f"unknown city {city_id!r}; known: {', '.join(sorted(CITIES))}") from None


def http_fetch(url: str, timeout: float = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "bike-or-bust-collector"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_with_retry(
    url: str,
    fetch: Fetcher = http_fetch,
    attempts: int = 4,
    base_delay: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> bytes:
    """Retry network errors and 5xx/429 with exponential backoff; fail fast on other 4xx."""
    for attempt in range(1, attempts + 1):
        try:
            return fetch(url)
        except urllib.error.HTTPError as e:
            if e.code < 500 and e.code != 429:
                raise FetchError(f"{url}: HTTP {e.code}") from e
            err: Exception = e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            err = e
        if attempt == attempts:
            raise FetchError(f"{url}: failed after {attempts} attempts: {err}") from err
        delay = base_delay * 2 ** (attempt - 1)
        log.warning("%s failed (%s); retry %d in %.1fs", url, err, attempt, delay)
        sleep(delay)
    raise AssertionError("unreachable")
