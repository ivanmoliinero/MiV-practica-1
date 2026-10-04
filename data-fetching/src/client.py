"""
client.py
---------
HTTP client session factory and resilient network request handlers with
Wikipedia-compliant rate-limiting, retry policies, and exponential backoff.
"""

import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from .config import HEADERS
except ImportError:
    from config import HEADERS

log = logging.getLogger("senate_scraper")


def create_session() -> requests.Session:
    """
    Creates a requests session configured with retries for transient HTTP errors
    (429, 500, 502, 503, 504) and custom project User-Agent headers.
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    retries = Retry(
        total=5,
        backoff_factor=3,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_with_backoff(
    session: requests.Session,
    url: str,
    params: dict | None = None,
    max_retries: int = 5,
) -> requests.Response:
    """
    Performs a GET request with explicit rate-limit handling (HTTP 429).
    If an HTTP 429 is encountered, respects the 'Retry-After' header if provided,
    or falls back to exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            response = session.get(url, params=params, timeout=25)
            if response.status_code == 429:
                retry_after_str = response.headers.get("Retry-After")
                retry_after = (
                    int(retry_after_str)
                    if retry_after_str and retry_after_str.isdigit()
                    else 10 * (attempt + 1)
                )
                log.warning(
                    "HTTP 429 received for %s. Backing off for %ds (attempt %d/%d)...",
                    url,
                    retry_after,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(retry_after)
                continue
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as exc:
            if attempt == max_retries - 1:
                raise exc
            wait = 4 * (attempt + 1)
            log.warning(
                "Request error for %s (%s). Retrying in %ds (attempt %d/%d)...",
                url,
                exc,
                wait,
                attempt + 1,
                max_retries,
            )
            time.sleep(wait)

    raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts")
