from fastapi import FastAPI

from agentgw.interfaces.http.controllers.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="agentgw")
    app.include_router(health_router)
    return app


def run() -> None:
    import uvicorn

    uvicorn.run(
        "agentgw.bootstrap.gateway_app:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
    )
