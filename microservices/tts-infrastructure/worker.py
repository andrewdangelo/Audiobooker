"""
ARQ Worker
==========
Separate process from uvicorn. Watches Redis for queued jobs and executes them.

Start with:
    python worker.py

In production you'd run this with a process manager (systemd, supervisor,
Docker CMD) alongside uvicorn. They are completely independent — restarting
uvicorn does not affect the worker and vice versa.

ARQ docs: https://arq-docs.helpmanual.io/
"""

import logging

import arq
from arq.connections import RedisSettings

from app.core.config_settings import settings
from app.core.logging_config import setup_logging
from app.services.book_generation_service import run_book_generation

setup_logging()
logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    """Called once when the worker process starts."""
    logger.info("ARQ worker starting up")


async def shutdown(ctx: dict) -> None:
    """Called once when the worker process shuts down."""
    logger.info("ARQ worker shutting down")


class WorkerSettings:
    """
    ARQ reads this class to configure the worker.

    functions    — the async functions this worker can execute.
                   ARQ matches job names to these at runtime.
    redis_settings — where Redis lives (same instance as the rest of the app).
    max_jobs     — max concurrent jobs this worker will run at once.
                   Keep at 1 for now since each job already uses TTS_CONCURRENCY
                   internally. Running 2 jobs simultaneously would mean
                   2 × TTS_CONCURRENCY concurrent HF calls.
    job_timeout  — seconds before ARQ considers a job hung and kills it.
                   Set generously: 500 chunks × 30s / TTS_CONCURRENCY ≈ 3000s.
    retry_jobs   — retry failed jobs automatically.
    max_tries    — how many total attempts before giving up.
    on_startup   — called when worker starts.
    on_shutdown  — called when worker stops.
    """
    functions = [run_book_generation]

    redis_settings = RedisSettings(
        host='127.0.0.1',
        port=6379,
        database=settings.REDIS_DB,
    )

    max_jobs = 1
    job_timeout = 3600        # 1 hour hard ceiling per job
    retry_jobs = True
    max_tries = 2             # 1 initial attempt + 1 retry on failure
    on_startup = startup
    on_shutdown = shutdown


if __name__ == "__main__":
    # Matt - I have this running as a Windows Service
    # import subprocess
    # subprocess.run('wsl -d Ubuntu-22.04 bash -c "sudo service redis start"', shell=True)
    
    arq.run_worker(WorkerSettings)