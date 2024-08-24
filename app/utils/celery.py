from celery.app import Celery
from decouple import config
from datetime import timedelta

redis_url = config("REDIS_URL")

celery = Celery(__name__, broker=redis_url, backend=redis_url, include=["app.tasks"])


# celery.conf.update(
#     task_serializer="json",
#     accept_content=["json"],
#     result_serializer="json",
#     timezone="UTC",
#     enable_utc=True,
# )

celery.autodiscover_tasks(["app"])
celery.conf.beat_schedule = {
    "refresh-every-hour": {
        "task": "app.tasks.refresh_data",  # "schedule": crontab(minute=0, hour="*"),  # Runs every hour
        "schedule": timedelta(
            hours=config("REFRESH_TIME_HOURS", cast=int)
        ),  # Runs every 1 seconds
    },
}
