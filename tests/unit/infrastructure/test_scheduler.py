import asyncio

import pytest

from agentgw.infrastructure.workers.scheduler import JobDefinition, Scheduler


@pytest.mark.asyncio
async def test_scheduler_continues_running_after_job_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    finished = asyncio.Event()
    original_sleep = asyncio.sleep

    async def flaky_job() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("transient")
        finished.set()

    async def fast_sleep(_: int) -> None:
        await original_sleep(0)

    monkeypatch.setattr("agentgw.infrastructure.workers.scheduler.asyncio.sleep", fast_sleep)
    scheduler = Scheduler([JobDefinition(name="flaky", interval_seconds=1, callback=flaky_job)])

    await scheduler.start()
    await asyncio.wait_for(finished.wait(), timeout=1)
    await scheduler.stop()

    assert calls >= 2
