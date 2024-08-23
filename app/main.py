"""Main module for the Gazette API, providing job and tender search functionality."""

from typing import Optional
from fastapi import FastAPI, Query
from api_analytics.fastapi import Analytics
from app.utils.constants import (
    JOB_CATEGORIES,
    IULAAN_TYPES,
)
from decouple import config
from app.utils.helpers import iulaan_search

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from redis import asyncio as aioredis
from tortoise.contrib.fastapi import register_tortoise
from tortoise.exceptions import NotExistOrMultiple
from app.models.models import Result, Result_Pydantic
import json


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    redis = aioredis.from_url(
        config(
            "REDIS_URL",
        )
    )
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    yield


app = FastAPI(title="Gazzette API", version="1.0.0", lifespan=lifespan)
app.add_middleware(Analytics, api_key=config("API_KEY"))  # Add middleware


@cache(expire=60)
@app.get("/search")
async def search(
    page: int = Query(1, ge=1),
    iulaan_type: Optional[str] = Query("", enum=list(IULAAN_TYPES.values())),
    category: Optional[str] = Query("", enum=list(JOB_CATEGORIES.values())),
    open_only: Optional[int] = Query(0, ge=0, le=1),
    start_date: Optional[str] = Query(""),
    end_date: Optional[str] = Query(""),
    q: Optional[str] = Query(""),
    office: Optional[str] = Query(""),
):
    """Search for iulaan listings based on provided parameters."""

    # Generate a unique key based on search parameters (URL or a hash)
    SEARCH_KEY = f"{iulaan_type}-{category}-{q}-{open_only}-{start_date}-{end_date}-{office}-{page}".strip()
    print(SEARCH_KEY)

    result_exists = await Result.filter(search_key=SEARCH_KEY).first()
    if result_exists:
        print(f"Result with key: {SEARCH_KEY} already exists. Fetching from DB.")
        response = await Result_Pydantic.from_tortoise_orm(result_exists)
        return response

    results = iulaan_search(
        category=category,
        iulaan_type=iulaan_type,
        open_only=open_only,
        start_date=start_date,
        end_date=end_date,
        office=office,
        q=q,
        page=page,
    )

    try:
        print(f"New key: {SEARCH_KEY}. Creating new result in DB.")
        new_result_obj = await Result.create(
            search_key=SEARCH_KEY, content=json.dumps(results)
        )
        response = await Result_Pydantic.from_tortoise_orm(new_result_obj)
        return response
    except NotExistOrMultiple:
        pass


register_tortoise(
    app,
    db_url=config("DATABASE_URL", cast=str),
    modules={"models": ["app.models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
