from app.utils.celery import celery
from app.utils.helpers import iulaan_search_with_url
from app.models.models import Result
import json
from tortoise.exceptions import DoesNotExist
import asyncio
from tortoise import Tortoise
from decouple import config
import time
import random
from app.utils.tg import notify_telegram


@celery.task
def refresh_data():
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    result = loop.run_until_complete(update_stale_results())
    return result


async def update_stale_results():
    await Tortoise.init(
        db_url=config("DATABASE_URL", cast=str),
        modules={"models": ["app.models"]},
    )

    total_results = await Result.all().count()
    print("TOTAL RESULTS -> ", total_results)
    updated_results_count = 0
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
    await asyncio.sleep(1)
    notify_telegram(number=updated_results_count)
    return "Database results Updated!"
