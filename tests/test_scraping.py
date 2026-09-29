"""Tests for gazette page fetching and parsing.

The fixture is a real search results page saved from gazette.gov.mv. If the
site's markup changes, re-save it and these tests show what broke.
"""

import asyncio
from pathlib import Path

import httpx
import pytest

from app.utils import helpers
from app.utils.helpers import UpstreamError, fetch_html, parse_listing

FIXTURE = Path(__file__).parent / "fixtures" / "iulaan_search.html"


class TestParseListing:
    @pytest.fixture(scope="class")
    def parsed(self):
        return parse_listing(FIXTURE.read_bytes())

    def test_meta_data(self, parsed):
        meta = parsed["meta_data"]
        assert meta["total_results"] == 142
        assert meta["total_pages"] == 15
        assert meta["current_page"] == 1
        assert meta["next_page_link"].endswith("page=2")

    def test_results(self, parsed):
        results = parsed["results"]
        assert len(results) == 10
        first = results[0]
        assert first["id"] == 412651
        assert first["url"] == "https://www.gazette.gov.mv/iulaan/412651"
        assert first["title"]
        assert first["vendor"]
        assert first["vendor_url"].startswith("/iulaan?office=")
        assert first["iulaan_type"]
        assert first["date"] == "2026-09-17T00:00:00"
        assert first["deadline"] == "2026-09-21T00:00:00"

    def test_every_result_has_required_fields(self, parsed):
        for item in parsed["results"]:
            assert {
                "id",
                "url",
                "title",
                "vendor",
                "vendor_url",
                "iulaan_type",
            } <= item.keys()

    def test_empty_page(self):
        assert parse_listing(b"<html><body></body></html>") == {
            "meta_data": {"total_results": 0},
            "results": [],
        }


def _fetch_with(handler):
    async def run():
        helpers._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        try:
            return await fetch_html("https://www.gazette.gov.mv/iulaan/")
        finally:
            await helpers.close_client()

    return asyncio.run(run())


class TestFetchHtml:
    def test_ok(self):
        assert (
            _fetch_with(lambda req: httpx.Response(200, content=b"<html/>"))
            == b"<html/>"
        )

    def test_timeout_raises_upstream_error(self):
        def handler(request):
            raise httpx.ReadTimeout("slow", request=request)

        with pytest.raises(UpstreamError):
            _fetch_with(handler)

    def test_non_200_raises_upstream_error(self):
        # Must not be treated as an empty result set, or it would get cached.
        with pytest.raises(UpstreamError):
            _fetch_with(lambda req: httpx.Response(503))

    def test_default_timeout_covers_slow_searches(self):
        # Keyword searches were measured at ~7s; httpx's 5s default caused 500s.
        assert helpers.GAZETTE_TIMEOUT.read >= 20
