from app.utils.procrastinate_app import procrastinate_app
from app.utils.helpers import iulaan_search_with_url
from app.models.models import Result
import json
from tortoise.exceptions import DoesNotExist
from tortoise import Tortoise
from decouple import config
import time
import random
from app.utils.tg import notify_telegram


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
    await Tortoise.init(
        db_url=config("DATABASE_URL", cast=str),
        modules={"models": ["app.models"]},
    )

    total_results = await Result.all().count()
    print("TOTAL RESULTS -> ", total_results)
    updated_results_count = 0
    start_time = time.time()

    for db_result in await Result.all():
        time.sleep(random.uniform(1, 5))
        try:
            actual_result = await iulaan_search_with_url(db_result.url)
            if db_result.content != actual_result:
                print("CONTENT CHANGED!!")
                updated_result_obj = await Result.filter(
                    search_key=db_result.search_key,
                ).update(content=json.dumps(actual_result))
                updated_results_count += 1
                print(updated_result_obj)
        except DoesNotExist:
            print("Does not exist")
        except Exception as e:
            print(e)

    end_time = time.time()
    total_duration = end_time - start_time

    notify_telegram(
        number=updated_results_count,
        total_rows=total_results,
        duration=total_duration,
    )
