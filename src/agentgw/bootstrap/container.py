from fastapi import FastAPI

from agentgw.interfaces.http.controllers.health import router as health_router


def build_app() -> FastAPI:
    app = FastAPI(title="agentgw")
    app.include_router(health_router)
    return app
