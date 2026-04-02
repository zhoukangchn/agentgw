from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class JobDefinition:
    name: str
    interval_seconds: int
    callback: Callable[[], Awaitable[None]]


class Scheduler:
    def __init__(self, jobs: list[JobDefinition]):
        self._jobs = jobs
        self._tasks: list[asyncio.Task[None]] = []
        self._started = False

    async def start(self) -> None:
        if self._started:
            return

        self._started = True
        for job in self._jobs:
            self._tasks.append(asyncio.create_task(self._run_job(job), name=f"scheduler:{job.name}"))

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self._started = False

    async def run_once(self) -> None:
        for job in self._jobs:
            await job.callback()

    async def _run_job(self, job: JobDefinition) -> None:
        while True:
            try:
                await job.callback()
            except asyncio.CancelledError:
                raise
            except Exception:
                pass
            await asyncio.sleep(job.interval_seconds)
