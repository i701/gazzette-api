"""Helper functions for the Gazette API."""

import re
from datetime import datetime

import httpx
from decouple import config
from selectolax.lexbor import LexborHTMLParser

from app.utils.constants import (
    GAZETTE_BASE_URL,
    IULAAN_SEARCH_URL,
    MONTH_TRANSLATIONS,
)

# gazette.gov.mv regularly takes 5-10s to answer keyword searches, which is
# longer than httpx's 5s default. Keep the read timeout generous.
GAZETTE_TIMEOUT = httpx.Timeout(
    config("GAZETTE_TIMEOUT_SECONDS", cast=float, default=30.0), connect=10.0
)


class UpstreamError(Exception):
    """Raised when gazette.gov.mv times out or returns a non-200 response."""


def detect_component(part):
    """Detect if the part is a day, month, year, or time."""
    if re.match(r"^\d{1,2}$", part):
        return "day"
    elif re.match(r"^\d{4}$", part):
        return "year"
    elif re.match(r"^\d{2}:\d{2}$", part):
        return "time"
    elif part in MONTH_TRANSLATIONS:
        return "month"
    return "unknown"


def maldivian_to_iso(date_str):
    """Convert a maldivian date string to ISO 8601."""
    parts = date_str.split()

    day = None
    month = None
    year = None
    time_str = None

    for part in parts:
        component_type = detect_component(part)
        if component_type == "day":
            day = part
        elif component_type == "month":
            month = MONTH_TRANSLATIONS.get(part, "Unknown")
        elif component_type == "year":
            year = part
        elif component_type == "time":
            time_str = part
    if day is None or month is None or year is None:
        raise ValueError("Date string is missing required components")

    if time_str is None:
        time_str = "00:00"

    date_formatted = f"{month} {day}, {year} {time_str}"

    try:
        dt_obj = datetime.strptime(date_formatted, "%B %d, %Y %H:%M")
    except ValueError:
        dt_obj = datetime.strptime(date_formatted, "%B %d, %Y")

    iso_date = dt_obj.isoformat()

    return iso_date


_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    """Return a shared client so connections (and TLS) are reused across requests."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=GAZETTE_TIMEOUT,
            # Retries connection failures only; read timeouts are not retried.
            transport=httpx.AsyncHTTPTransport(retries=2),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def fetch_html(url: str) -> bytes:
    """Fetch a gazette page, raising UpstreamError on timeouts or bad responses."""
    try:
        response = await get_client().get(url)
    except httpx.TimeoutException as e:
        raise UpstreamError(f"Timed out fetching {url}") from e
    except httpx.HTTPError as e:
        raise UpstreamError(f"Error fetching {url}: {e!r}") from e
    if response.status_code != 200:
        raise UpstreamError(f"Got HTTP {response.status_code} from {url}")
    return response.content


def parse_listing(html: bytes) -> dict:
    """Parse an iulaan listing page into meta data and results."""
    tree = LexborHTMLParser(html)
    meta_data = {}
    results = []

    total = tree.css_first("div.iulaan-type-title")
    meta_data["total_results"] = (
        int(total.text().split(" ")[1].strip()) if total is not None else 0
    )

    pagination = tree.css_first("ul.pagination")
    if pagination is not None:
        page_items = pagination.css("li")
        if len(page_items) > 1:
            meta_data["total_pages"] = int(page_items[-2].text().strip())
        else:
            meta_data["total_pages"] = 1

        active = pagination.css_first("li.active")
        meta_data["current_page"] = int(active.text().strip()) if active else 1

        next_page_link = None
        if len(page_items) > 1:
            last_link = page_items[-1].css_first("a")
            if last_link is not None:
                next_page_link = last_link.attributes.get("href")
        meta_data["next_page_link"] = next_page_link

    for item in tree.css("div.items"):
        item_body = {}

        title = item.css_first("a.iulaan-title")
        item_body["url"] = title.attributes.get("href")
        item_body["id"] = [
            int(segment) for segment in item_body["url"].split("/") if segment.isdigit()
        ][0]
        item_body["title"] = title.text()

        vendor = item.css_first("a.iulaan-office")
        iulaan_type = item.css_first("a.iulaan-type")

        item_body["vendor"] = vendor.text().strip()
        item_body["vendor_url"] = vendor.attributes.get("href").strip()
        item_body["iulaan_type"] = iulaan_type.text().strip()

        for info in item.css("div.info"):
            text = info.text().strip()
            has_time = any(re.match(r"^\d{2}:\d{2}$", p) for p in text.split())
            try:
                parsed = maldivian_to_iso(text)
                if has_time:
                    item_body["deadline"] = parsed
                else:
                    item_body["date"] = parsed
            except ValueError:
                pass

        results.append(item_body)

    return {"meta_data": meta_data, "results": results}


async def iulaan_search(
    page: int = 1,
    iulaan_type: str = "",
    category: str | None = "",
    q: str | None = "",
    open_only: int = 0,
    start_date: str | None = "",
    end_date: str | None = "",
    office: str | None = "",
) -> tuple[dict, str]:
    """Search for job and tender listings based on provided parameters."""
    url = (
        f"{GAZETTE_BASE_URL}{IULAAN_SEARCH_URL}?"
        f"type={iulaan_type}&job-category={category}"
        f"&office={office}&page={page}"
        f"&start-date={start_date}&end-date={end_date}"
        f"&open-only={open_only}"
        f"&q={q}"
    )
    return parse_listing(await fetch_html(url)), url


async def iulaan_search_with_url(url: str) -> dict:
    """Search for listings from url."""
    return parse_listing(await fetch_html(url))
