"""Procrastinate worker entry point."""

import asyncio
import psycopg_pool
from decouple import config
from app.utils.procrastinate_app import procrastinate_app
import app.tasks  # noqa: F401 — registers tasks with procrastinate_app


DATABASE_URL = config("DATABASE_URL").replace("postgres://", "postgresql://")


async def main() -> None:
    async with psycopg_pool.AsyncConnectionPool(
        conninfo=DATABASE_URL, open=False
    ) as pool:
        async with procrastinate_app.open_async(pool=pool):
            await procrastinate_app.run_worker_async()


if __name__ == "__main__":
    asyncio.run(main())
