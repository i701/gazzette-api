import asyncio
import json
import logging
import random
import time
from datetime import timedelta

from decouple import config
from tortoise import timezone

from app.models.models import Result
from app.utils.helpers import iulaan_search_with_url
from app.utils.procrastinate_app import procrastinate_app
from app.utils.tg import notify_telegram

logger = logging.getLogger(__name__)

# Rows not requested for this long are deleted.
PURGE_AFTER_DAYS = config("PURGE_AFTER_DAYS", cast=int, default=7)
# Only rows requested within this window are refreshed; the rest are left
# alone until they are requested again (then refreshed) or purged.
REFRESH_ACTIVE_HOURS = config("REFRESH_ACTIVE_HOURS", cast=int, default=24)
# Parallel requests to gazette.gov.mv during a refresh. Kept low to be polite.
REFRESH_CONCURRENCY = config("REFRESH_CONCURRENCY", cast=int, default=3)


_refresh_minutes = config("REFRESH_TIME_MINUTES", cast=int, default=60)
if _refresh_minutes < 60:
    _cron = f"*/{_refresh_minutes} * * * *"
elif _refresh_minutes % 60 == 0:
    _hours = _refresh_minutes // 60
    _cron = "0 * * * *" if _hours == 1 else f"0 */{_hours} * * *"
else:
    _cron = "0 * * * *"


@procrastinate_app.periodic(cron=_cron)
@procrastinate_app.task
async def refresh_data(timestamp: int) -> None:
    await update_stale_results()


async def purge_unused_results() -> int:
    """Delete rows nobody has requested in PURGE_AFTER_DAYS."""
    cutoff = timezone.now() - timedelta(days=PURGE_AFTER_DAYS)
    return await Result.filter(last_accessed_at__lt=cutoff).delete()


async def _refresh_one(db_result: Result, semaphore: asyncio.Semaphore) -> bool:
    """Re-scrape one row. Returns True if its content changed."""
    async with semaphore:
        await asyncio.sleep(random.uniform(0.5, 2))
        try:
            actual_result = await iulaan_search_with_url(db_result.url)
        except Exception as e:
            logger.error("Error updating result %s: %s", db_result.search_key, e)
            return False
    # JSONField gives back the decoded value, so compare parsed data to parsed data.
    if db_result.content == actual_result:
        return False
    logger.info("Content changed for key: %s", db_result.search_key)
    await Result.filter(id=db_result.id).update(content=json.dumps(actual_result))
    return True


async def update_stale_results():
    start_time = time.time()
    purged = await purge_unused_results()

    active_since = timezone.now() - timedelta(hours=REFRESH_ACTIVE_HOURS)
    active = await Result.filter(last_accessed_at__gte=active_since)
    total_results = await Result.all().count()
    logger.info(
        "Purged %d unused results. Refreshing %d active of %d total.",
        purged,
        len(active),
        total_results,
    )

    semaphore = asyncio.Semaphore(REFRESH_CONCURRENCY)
    changed = await asyncio.gather(*(_refresh_one(r, semaphore) for r in active))
    updated_results_count = sum(changed)

    total_duration = time.time() - start_time
    logger.info(
        "Done. %d/%d results updated, took %.1fs.",
        updated_results_count,
        len(active),
        total_duration,
    )
    notify_telegram(
        number=updated_results_count,
        total_rows=total_results,
        duration=total_duration,
        purged=purged,
    )
