import json
import logging
import random
import time

from decouple import config
from tortoise.exceptions import DoesNotExist

from app.utils.procrastinate_app import procrastinate_app
from app.utils.helpers import iulaan_search_with_url
from app.models.models import Result
from app.utils.tg import notify_telegram

logger = logging.getLogger(__name__)


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


async def update_stale_results():
    total_results = await Result.all().count()
    logger.info("Updating stale results. Total in DB: %d", total_results)
    updated_results_count = 0
    start_time = time.time()

    for db_result in await Result.all():
        time.sleep(random.uniform(1, 5))
        try:
            actual_result = await iulaan_search_with_url(db_result.url)
            if db_result.content != actual_result:
                logger.info("Content changed for key: %s", db_result.search_key)
                await Result.filter(search_key=db_result.search_key).update(
                    content=json.dumps(actual_result)
                )
                updated_results_count += 1
        except DoesNotExist:
            pass
        except Exception as e:
            logger.error("Error updating result %s: %s", db_result.search_key, e)

    total_duration = time.time() - start_time
    logger.info(
        "Done. %d/%d results updated, took %.1fs.",
        updated_results_count, total_results, total_duration,
    )
    notify_telegram(
        number=updated_results_count,
        total_rows=total_results,
        duration=total_duration,
    )
