from agentgw.bootstrap.container import build_app


def create_app():
    return build_app()


def run() -> None:
    import uvicorn

    uvicorn.run(
        "agentgw.bootstrap.gateway_app:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
    )
