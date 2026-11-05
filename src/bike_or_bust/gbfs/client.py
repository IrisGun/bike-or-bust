"""HTTP access to the GBFS feeds: fetching with retry. Knows nothing about storage."""

from __future__ import annotations

import logging
import time
import urllib.error
import urllib.request
from collections.abc import Callable

log = logging.getLogger(__name__)

BASE_URL = "https://gbfs.lyft.com/gbfs/1.1/bkn/en"
FEEDS = ("station_status", "station_information")

Fetcher = Callable[[str], bytes]


class FetchError(Exception):
    """The source could not be read or returned unusable data (not a bug in our code)."""


def feed_url(feed: str) -> str:
    return f"{BASE_URL}/{feed}.json"


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
