from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agentgw.bootstrap.container import Container, build_app, build_container


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container: Container = app.state.container
    await container.delivery_dispatcher.start()
    if container.settings.scheduler_enabled:
        await container.scheduler.start()
    try:
        yield
    finally:
        if container.settings.scheduler_enabled:
            await container.scheduler.stop()
        await container.delivery_dispatcher.stop()


def create_app() -> FastAPI:
    container = build_container()
    app = build_app(container)
    app.router.lifespan_context = lifespan
    return app


def run() -> None:
    import uvicorn

    uvicorn.run(
        "agentgw.bootstrap.gateway_app:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
    )
