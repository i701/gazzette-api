"""Procrastinate worker entry point."""

import asyncio
import logging
import psycopg_pool
from decouple import config
from tortoise import Tortoise
from app.utils.procrastinate_app import procrastinate_app
import app.tasks  # noqa: F401 — registers tasks with procrastinate_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


DATABASE_URL = config("DATABASE_URL").replace("postgres://", "postgresql://")


async def main() -> None:
    await Tortoise.init(
        db_url=config("DATABASE_URL"),
        modules={"models": ["app.models"]},
    )
    try:
        async with psycopg_pool.AsyncConnectionPool(
            conninfo=DATABASE_URL, open=False
        ) as pool:
            async with procrastinate_app.open_async(pool=pool):
                await procrastinate_app.run_worker_async()
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
