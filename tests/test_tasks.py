"""Tests for purging unused results and refreshing only active ones."""

import asyncio
import json
from datetime import timedelta
from unittest.mock import patch

from tortoise import Tortoise, timezone

from app import tasks
from app.models.models import Result
from app.utils.helpers import UpstreamError


def run_with_db(coro_fn):
    async def run():
        await Tortoise.init(
            db_url="sqlite://:memory:", modules={"models": ["app.models"]}
        )
        await Tortoise.generate_schemas()
        try:
            return await coro_fn()
        finally:
            await Tortoise.close_connections()

    return asyncio.run(run())


async def make_result(key, accessed_ago, content="{}"):
    return await Result.create(
        search_key=key,
        url=f"https://example.test/{key}",
        content=content,
        last_accessed_at=timezone.now() - accessed_ago,
    )


def test_purge_deletes_only_rows_unused_past_cutoff():
    async def scenario():
        await make_result("fresh", timedelta(hours=1))
        await make_result("borderline", timedelta(days=tasks.PURGE_AFTER_DAYS - 1))
        await make_result("old", timedelta(days=tasks.PURGE_AFTER_DAYS + 1))
        purged = await tasks.purge_unused_results()
        remaining = sorted(await Result.all().values_list("search_key", flat=True))
        return purged, remaining

    purged, remaining = run_with_db(scenario)
    assert purged == 1
    assert remaining == ["borderline", "fresh"]


def test_refresh_only_touches_active_rows_and_saves_changes():
    new_content = {"meta_data": {}, "results": [{"id": 1}]}
    fetched = []

    async def fake_search(url):
        fetched.append(url)
        return new_content

    async def scenario():
        await make_result("active-changed", timedelta(hours=1))
        await make_result(
            "active-same", timedelta(hours=2), content=json.dumps(new_content)
        )
        await make_result("idle", timedelta(hours=tasks.REFRESH_ACTIVE_HOURS + 1))
        with (
            patch.object(tasks, "iulaan_search_with_url", fake_search),
            patch.object(tasks, "notify_telegram") as notify,
            patch.object(tasks.random, "uniform", return_value=0),
        ):
            await tasks.update_stale_results()
        rows = {r.search_key: r.content for r in await Result.all()}
        return rows, notify.call_args.kwargs

    rows, notified = run_with_db(scenario)
    assert sorted(fetched) == [
        "https://example.test/active-changed",
        "https://example.test/active-same",
    ]
    assert rows["active-changed"] == new_content
    assert rows["active-same"] == new_content
    assert rows["idle"] == {}
    assert notified["number"] == 1
    assert notified["total_rows"] == 3


def test_refresh_survives_upstream_errors():
    async def failing_search(url):
        raise UpstreamError("down")

    async def scenario():
        await make_result("active", timedelta(hours=1))
        with (
            patch.object(tasks, "iulaan_search_with_url", failing_search),
            patch.object(tasks, "notify_telegram") as notify,
            patch.object(tasks.random, "uniform", return_value=0),
        ):
            await tasks.update_stale_results()
        return (await Result.get(search_key="active")).content, notify.call_args.kwargs

    content, notified = run_with_db(scenario)
    assert content == {}
    assert notified["number"] == 0
